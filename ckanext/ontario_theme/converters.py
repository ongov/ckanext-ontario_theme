# coding=utf-8
import logging
import re
import requests
import ckan
import json
import html2text

# do we need all these?
from hashlib import sha1
import traceback
import uuid
import xml.etree.ElementTree as ElementTree
import lxml.etree # New import, TODO: change old usage of xml.etree to this.
import datetime
import csv

from ckanext.ontario_theme import helpers as ontario_theme_helpers
import ckan.plugins.toolkit as toolkit
from ckan import model

log = logging.getLogger(__name__)

today = datetime.datetime.now()
today_iso = today.strftime("%Y-%m-%d")

# pattens for digging around in the ontario geohub description
geohub_contact_pattern = re.compile("\*\*Contact(?:[\*\s\n]*)([a-zA-Z0-9&\(\)\/\. \-,\s\n@ \]\[]*)(?:\s*)(?:\n*)\[([\na-zA-Z0-9\.]*@[oO]ntario.ca)\]")
geohub_fr_contact_pattern = re.compile(u"\*\*Personne-resource(?:[\*\s\n]*)([\u00A0-\u017Fa-zA-Z0-9&\(\)\/\. \-,\s\n@ \]\[]*)(?:\s*)(?:\n*)\[([\na-zA-Z0-9\.]*@[oO]ntario.ca)\]")
ontario_email_pattern = re.compile("[a-zA-Z0-9\.]*@[oO]ntario.ca")
iso_date_pattern = re.compile("[0-9]{4}-[0-9]{2}-[0-9]{2}")
geohub_update_frequency_pattern = re.compile("\*\*Maintenance and Update Frequency(?:[\s\n]*)\*\*(?:[\s\n]*)([a-zA-Z0-9 ]*):")

calls_to_infogo = {}

update_frequencies = {
    "Irregular": "periodically",
    "Continual": "current",
    "Annually": "yearly",
    "Unknown": "other",
    "Weekly": "weekly",
    "Monthly": "monthly",
    "Fortnightly": "fortnightly",
    "Quarterly": "quarterly",
    "Biannually": "biannually",
    "As needed": "as_required",
    "On going": "as_required",
    "Not planned": "never",
    "As Needed": "as_required"
}

ministries = {
    "Ontario Ministry of Natural Resources and Forestry" : "natural-resources-and-forestry",
    #"Ontario Ministry of Natural Resources" : "natural-resources-and-forestry",
    "Ontario Ministry of Children, Community and Social Services" : "children-community-and-social-services",
    "Ontario Ministry of Health" : "health",
    "Ontario Ministry of Long-term care" : "long-term-care",
    "Ontario Ministry of Government and Consumer Services" : "government-and-consumer-services",
    "Ontario Ministry of Environment, Conservation and Parks" : "environment-conservation-and-parks",
    "Ontario Ministry of Energy, Northern Development and Mines" : "energy-northern-development-and-mines",
    "Ontario Ministry of Municipal Affairs and Housing" : "municipal-affairs-and-housing",
    "Ontario Ministry of Education" : "education",
    "Ontario Ministry of Agriculture Food and Rural Affairs" : "agriculture-food-and-rural-affairs",
    "Ontario Ministry of Transportation" : "transportation"
}

geohub_metadata_ministry_names = {
    "Ontario Ministry of Natural Resources and Forestry" : "natural-resources-and-forestry",
    "Ontario Ministry of Agriculture, Food and Rural Affairs" : "agriculture-food-and-rural-affairs",
    "Ontario Ministry of the Environment, Conservation and Parks" : "environment-conservation-and-parks",
    "Ontario Ministry of Transportation" : "transportation",
    "Ontario Ministry of Health" : "health",
    "Ontario Ministry of Education" : "education",
    "Ontario Ministry of Municipal Affairs and Housing" : "municipal-affairs-and-housing",
    "Ontario Ministry of Natural Resources and Forestry - Provincial Mapping Unit" : "natural-resources-and-forestry",
    "Ontario Ministry of Indigenous Affairs": "indigenous-affairs",
    "Ontario Ministry of Energy, Northern Development and Mines" : "energy-northern-development-and-mines"    
}

infogo_ministry_names = {
    "Agriculture, Food and Rural Affairs" : "agriculture-food-and-rural-affairs",
    "Attorney General" : "attorney-general",
    "Cabinet Office" : "cabinet-office",
    "Children, Community and Social Services" : "children-community-and-social-services",
    "Colleges and Universities" : "colleges-and-universities",
    "Economic Development, Job Creation and Trade" : "economic-development-job-creation-and-trade",
    "Education" : "education",
    "Energy, Northern Development and Mines" : "energy-northern-development-and-mines",
    "Environment, Conservation and Parks" : "environment-conservation-and-parks",
    "Finance" : "finance",
    "Francophone Affairs" : "francophone-affairs",
    "Government and Consumer Services" : "government-and-consumer-services",
    "Health" : "health",
    "Heritage, Sport, Tourism and Culture Industries" : "heritage-sport-tourism-and-culture-industries",
    "Indigenous Affairs" : "indigenous-affairs",
    "Infrastructure" : "infrastructure",
    "Intergovernmental Affairs" : "intergovernmental-affairs",
    "Labour, Training and Skills Development" : "labour-training-and-skills-development",
    "Long-Term Care" : "long-term-care",
    "Municipal Affairs and Housing" : "municipal-affairs-and-housing",
    "Natural Resources and Forestry" : "natural-resources-and-forestry",
    "Seniors and Accessibility" : "seniors-and-accessibility",
    "Solicitor General" : "solicitor-general",
    "Transportation" : "transportation",
    "Treasury Board Secretariat" : "treasury-board-secretariat"
}

org_ids = {
    
}


def get_org_id(organization_name):     
    if organization_name in org_ids:
        return org_ids[organization_name]
    return False


def call_to_infogo(email):
    if email not in calls_to_infogo:
        infogo_request = requests.get("http://www.infogo.gov.on.ca/infogo/v1/individuals/search?&keywords={}".format(email))
        calls_to_infogo[email] = infogo_request.json()
    return calls_to_infogo[email]


def extract_update_frequency(description):
    search_results = geohub_update_frequency_pattern.findall(description)
    if len(search_results) > 0:
        return search_results[0].strip()
    else:
        return None


geohub_description_fr__ministry_names = {
    "Ministère des Richesses naturelles et des Forêts de l'Ontario": "natural-resources-and-forestry",
    "Ministère de l'Agriculture, de l'Alimentation et des Affaires rurales de l'Ontario": "agriculture-food-and-rural-affairs",
    "Ministère des Richesses naturelles et des Forêts": "natural-resources-and-forestry",
    "Ministère de l’Environnement, de la Protection de la nature et des Parcs de l'Ontario": "environment-conservation-and-parks",    
    "Ministère de l’Environnement, de la Protection de la nature et des Parcs": "environment-conservation-and-parks",
    "Ministère des Richesses naturelles": "natural-resources-and-forestry",
    "Ministère de l’Énergie, Développement du Nord et Mines": "energy-northern-development-and-mines"
}


def extract_fr_contact_info(description):
    search_results = geohub_contact_pattern.findall(description)
    if len(search_results) > 0:
        contact_info = search_results[0]
        # split into maintainer name, ministry, branch, email
        contact_info_dict = {
            "maintainer_email" : contact_info[1]
        }
        non_email_contact_info = contact_info[0].replace("\n"," ").replace("  "," ")
        for ministry in geohub_description_fr_ministry_names.keys():
            ministry_pattern = re.compile("("+ministry+"[\s\n-,.]*)")
            look_for_ministry = ministry_pattern.findall(non_email_contact_info, re.IGNORECASE)
            if len(look_for_ministry) > 0:
                ministry_result = look_for_ministry[0]
                # there's a ministry name in there. let's take it out and use the rest as a maintainer name
                non_email_contact_info = non_email_contact_info.replace(ministry_result[0], "").strip()
                contact_info_dict['ministry'] = geohub_description_fr_ministry_names[ministry.strip()]
                break
            if non_email_contact_info.lower().find("direction") != -1:
                contact_info_chunks = non_email_contact_info.split(",")
                for chunk in contact_info_chunks:
                    if chunk.lower().find("direction") != -1:
                       contact_info_dict['maintainer_branch'] = chunk
                       break  
        contact_info_dict['maintainer_name'] = non_email_contact_info.strip()
        if contact_info_dict['maintainer_name'][-1] in ["-",","]:
            contact_info_dict['maintainer_name'] = contact_info_dict['maintainer_name'][:-1].strip() 
        return contact_info_dict
    else:
        return None


geohub_description_ministry_names = {
    "Ontario Ministry of Natural Resources and Forestry": "natural-resources-and-forestry",
    "Ontario Ministry of Agriculture, Food and Rural Affairs": "agriculture-food-and-rural-affairs",
    "Ontario Ministry of the Environment, Conservation and Parks": "environment-conservation-and-parks",
    "Ontario Ministry of Natural Resources": "natural-resources-and-forestry",
    "Ministry of Natural Resources and Forestry": "natural-resources-and-forestry",
    "Ministry of the Environment Conservation and Parks": "environment-conservation-and-parks",
    "Ministry of the Environment, Conservation and Parks": "environment-conservation-and-parks",
    "Ministry of Energy, Northern Development and Mines": "energy-northern-development-and-mines",
    "Ministry of Environment, Conservation and Parks" : "environment-conservation-and-parks",
    "Ministry of Health and Long-Term Care (MOHLTC)": "health"
}


def extract_contact_info(description):
    search_results = geohub_contact_pattern.findall(description)
    if len(search_results) > 0:
        contact_info = search_results[0]
        # split into maintainer name, ministry, branch, email
        contact_info_dict = {
            "maintainer_email" : contact_info[1].strip()
        }
        non_email_contact_info = contact_info[0].replace("\n"," ").replace("  "," ")
        for ministry in geohub_description_ministry_names.keys():
            ministry_pattern = re.compile("("+ministry+"[\s\n-,.]*)")
            look_for_ministry = ministry_pattern.findall(non_email_contact_info, re.IGNORECASE)
            if len(look_for_ministry) > 0:
                # there's a ministry name in there. let's take it out and use the rest as a maintainer name
                non_email_contact_info = non_email_contact_info.replace(look_for_ministry[0], "").strip()
                contact_info_dict['ministry'] = geohub_description_ministry_names[ministry.strip()]
                break
            if non_email_contact_info.lower().find("branch") != -1:
                contact_info_chunks = non_email_contact_info.split(",")
                for chunk in contact_info_chunks:
                    if chunk.lower().find("branch") != -1:
                       contact_info_dict['maintainer_branch'] = chunk
                       break  
        contact_info_dict['maintainer_name'] = non_email_contact_info.strip()
        if contact_info_dict['maintainer_name'][-1] in ["-",","]:
            contact_info_dict['maintainer_name'] = contact_info_dict['maintainer_name'][:-1].strip()
        return contact_info_dict
    else:
        return None


def extract_date(date_str):
    search_results = iso_date_pattern.findall(date_str)
    if len(search_results) > 0:
        return search_results[0]
    else:
        return None


def extract_ministry(description, email):
    for ministry_search_text, ministry_name in ministries.items():
        if description.find(ministry_search_text):
            return ministry_name

    infogo_response = call_to_infogo(email)
    if 'individuals' in infogo_response:
        for individual_record in infogo_response['individuals']:
            if individual_record['topOrgName'] in infogo_ministry_names:
                return infogo_ministry_names[individual_record['topOrgName']]
    else:
        return "natural-resources-and-forestry"


def extract_ontario_email(description):
    search_results = ontario_email_pattern.findall(description)
    if len(search_results) > 0:
        return search_results[0]
    else:
        return None


def get_ontario_employee_name(email):
    return " ".join(list(map(lambda x: x.capitalize(), re.sub(r'[0-9]+', '', email).replace("@ontario.ca","").split(".", 1))))
    # request timing out right now. reenable this later
    infogo_response = call_to_infogo(email)
    if infogo_response['total'] > 0:
        calls_to_infogo[email] = infogo_response
        return " ".join(list(map(lambda x: infogo_response['individuals'][0][x] if x in infogo_response['individuals'][0] else "", ["firstname", "middleName","lastName"])))
    else:
        return " ".join(list(map(lambda x: x.capitalize(), re.sub(r'[0-9]+', '', email).replace("@ontario.ca","").split(".", 1))))


def french_notes(french_xml):
    '''Returns the french notes from the xml response.
    <dataIdInfo><idAbs>
    '''
    french_notes_text = 'Placeholder'

    root = french_xml
    #root = lxml.etree.fromstring(french_xml.content)
    french_notes_element = root.xpath("//dataIdInfo/idAbs")
    if french_notes_element:
        french_notes_text = french_notes_element[0].text

    return french_notes_text


def french_title(french_xml):
    '''Returns the french title from the xml response.
    <dataIdInfo><idCitation><resTitle>
    '''
    french_title_text = 'Placeholder'

    root = french_xml
    #root = lxml.etree.fromstring(french_xml.content)
    french_title_element = root.xpath("//dataIdInfo/idCitation/resTitle")
    if french_title_element:
        french_title_text = french_title_element[0].text

    return french_title_text


def french_keywords(french_xml):
    '''Returns array of french keywords from the xml response.
    searchKeys matches data.json keywords that are used for english record.
    '''

    french_keywords = []

    root = french_xml
    #root = lxml.etree.fromstring(french_xml.content)
    french_keywords_element = root.xpath("//searchKeys")
    if french_keywords_element:
        for keyword in french_keywords_element[0]:
            french_keywords.append(keyword.text)
      
    return french_keywords


def get_license_from_xml(root):
    '''Returns the license for that dataset.
    '''

    for dataIdInfo in root.iter('dataIdInfo'):
        for resConst in dataIdInfo.iter('resConst'):
            for LegConsts in resConst.iter('LegConsts'):
                for useLimit in LegConsts.iter('useLimit'):
                    license = useLimit.text
                    return license


def get_revised_date_from_xml(root):
    '''Returns the license for that dataset.
    '''

    for dataIdInfo in root.iter('dataIdInfo'):
        for idCitation in dataIdInfo.iter('idCitation'):
            for dte in idCitation.iter('date'):
                for reviseDate in dte.iter('reviseDate'):
                    date_str = reviseDate.text
                    revised_date = extract_date(date_str)
                    if revised_date:
                        return revised_date
    return False


def get_ministry_from_xml(root):
    '''Returns the license for that dataset.
    '''

    for dataIdInfo in root.iter('dataIdInfo'):
        for idCitation in dataIdInfo.iter('idCitation'):
            for citRespParty in idCitation.iter('citRespParty'):
                for rpOrgName in citRespParty.iter('rpOrgName'):
                    ministry = rpOrgName.text
                    if ministry in geohub_metadata_ministry_names:
                        return geohub_metadata_ministry_names[ministry]
    return False


def build_resources(distribution, id, english_xml, dataset_url):
    resources = []

    for resource in distribution:
        resource_dict = { 
                    "name": resource["title"],
                    "type": 'data',
                    "description_translated": {
                        "en": "Preview and download via [Ontario GeoHub]({})".format(dataset_url),
                        "fr": "Preview and download via [Ontario GeoHub]({})".format(dataset_url)
                  },
                    "format": resource["mediaType"],
                    "url": resource.get("accessURL", "") }
        revised_date = get_revised_date_from_xml(english_xml)
        if revised_date:
            resource_dict['data_last_updated'] = revised_date
        resources.append(
                    resource_dict
                  ) # Some resources are missing links

    # Add in the metadata URLs
    resources.append(
                  { "name": "Metadata in ISO 19115 NAP Format",
                    "type": 'technical_document',
                    "description_translated": {
                        "en": "Preview and download via [Ontario GeoHub]({})".format(dataset_url),
                        "fr": "Preview and download via [Ontario GeoHub]({})".format(dataset_url)
                  },
                    "format": "html",
                    "url": "https://www.arcgis.com/sharing/rest/content/items/{}/info/metadata/metadata.xml?format=default&output=html".format(id) })
    resources.append(
                  { "name": "Metadata in Full Esri Format",
                    "type": 'technical_document',
                    "description_translated": {
                        "en": "Preview and download via [Ontario GeoHub]({})".format(dataset_url),
                        "fr": "Preview and download via [Ontario GeoHub]({})".format(dataset_url)
                  },
                    "format": "xml",
                    "url": metadata_url(id) })

    # Include resources from XML, putting them first.
    complete_resources = additional_resources_from_xml(english_xml) + resources

    return complete_resources


def geohub_french_id_from_xml(english_id):
    '''Return the french id from the english xml or empty string if not record.
    It's only available in the ?format=default version, so a seperate call.
    '''

    # Prime for no French ID.
    geohub_french_record_id_text = ''

    # Get resources from XML.
    metadata_xml_request = requests.get(metadata_url(english_id))
    # parse the response.
    root = lxml.etree.fromstring(metadata_xml_request.content)

    # Get the element then grab the text.
    
    # this works if using xml?format=default which I thought I had to use to access the ID value but turns out I don't. this also required namespacing.
    #geohub_french_record_id_element = root.xpath("//default:MD_Identifier[default:authority/default:CI_Citation/default:title/gco:CharacterString/text() = 'Ontario GeoHub French Record ID']/default:code/gco:CharacterString", namespaces=ns)
    geohub_french_record_id_element = root.xpath("//citId[identAuth/resTitle/text() = 'Ontario GeoHub French Record ID']/identCode")
    if geohub_french_record_id_element:
        geohub_french_record_id_text = geohub_french_record_id_element[0].text

    return geohub_french_record_id_text


def identifier_from_url(identifier_url):
    '''Accepts a string of the identifier URL that's part of data.json for 
    each dataset/record, and parses into just ID.
    '''
    # ID is at the end but sometimes there's extra bits we dont want that are
    # the underlying layer index.
    identifier = identifier_url.split('/')[-1].split('_')[0]
    return identifier


def identifier_from_url_with_index(identifier_url):
    '''Returns a string id with the layer index if it exists.
    '''
    identifier = identifier_url.split('/')[-1] # keep layer index.
    return identifier


def metadata_url(id):
    '''Returns a url for the metadata XML.
    '''
    return "https://www.arcgis.com/sharing/rest/content/items/{}/info/metadata/metadata.xml".format(id)


def additional_resources_from_xml(root):
    '''Returns array of dicts for additional resources.
    '''
    additional_resources = []
    for onLineSrc in root.iter('onLineSrc'):
        # Some datasets/records don't have additional resources so setting 
        # default values. They seem to use the data source instead without a name.
        additional_resources.append(
            {"url": onLineSrc.findtext('linkage'),
             "name": onLineSrc.findtext('orName',
                                        default=onLineSrc.findtext('linkage')),
             "type": 'data'}
            )
    return additional_resources


def english_metadata_xml_response(english_identifier):
    '''Returns the english metadata xml
    '''

    english_id = identifier_from_url(english_identifier)
    english_metadata_url = metadata_url(english_id)
    metadata_xml_request = requests.get(english_metadata_url)
    # parse the response to get the additional resources.
    root = ElementTree.fromstring(metadata_xml_request.content)
    return root


def french_metadata_xml_response(english_identifier):
    '''Returns the french metadata xml.
    To build this we need to grab the french values for some fields. Easiest
    so far is to loop over english and make a call to the matching french
    record. This will be used for a few payload values so calling once here.
    '''

    english_id = identifier_from_url(english_identifier)
    french_id = geohub_french_id_from_xml(english_id)
    french_id = identifier_from_url(french_id)
    french_metadata_xml_url = metadata_url(french_id)
    # Now can make request for xml.
    french_xml_response = requests.get(french_metadata_xml_url)

    try:
        # TODO: fix bug.  if geohub_french_id_from_xml: continue on, else abort french and use defaults. in some cases there is an ID but the request fails (outdated data I think). In this case it tries to parse the html I think and uses the defaults (den-site is an example).
        # TODO: Error handle for non-existent French record.
        french_xml_root = lxml.etree.fromstring(french_xml_response.content)
    except lxml.etree.XMLSyntaxError as e:
        logging.warning('Exception raised. Cannot parse response for english_id: {} and french_id: {}, likely not XML. Using empty root element instead. {}'
            .format(english_id, french_id, repr(e)))
        # Create an empty root element 
        french_xml_root = lxml.etree.Element("root")

    return french_xml_root


def _admin_user():
    context = {"model": model, "session": model.Session, "ignore_auth": True}
    return toolkit.get_action("get_site_user")(context, {})


def dcat_to_ontario(dcat_dict):

    organizations = model.Group.all("organization")
    for org in organizations:
        org_ids[org.name] = org.id

    english_xml = english_metadata_xml_response(dcat_dict['identifier'])
    french_xml = french_metadata_xml_response(dcat_dict['identifier']) 

    package_dict = {
        "id": identifier_from_url_with_index(dcat_dict['identifier']), # Use geohub ID.
        "url": dcat_dict["landingPage"],
        "license_id": "other-open", 
        "title_translated": {
            "en": dcat_dict["title"],
            "fr": french_title(french_xml)
        },
        "notes_translated": {
            "en": html2text.html2text(dcat_dict["description"]),
            "fr": html2text.html2text(french_notes(french_xml))
        },
        "keywords": {
            "en": ontario_theme_helpers.remove_odd_chars_from_keywords(dcat_dict["keyword"]) + ['ontario-geohub'],
            "fr": ontario_theme_helpers.remove_odd_chars_from_keywords(french_keywords(french_xml)) + ['ontario-geohub']
        },
        "opened_date": ontario_theme_helpers.date_parse(dcat_dict["issued"], '%Y-%m-%dT%H:%M:%S.%fZ'),
        "current_as_of": ontario_theme_helpers.date_parse(dcat_dict["modified"], '%Y-%m-%dT%H:%M:%S.%fZ'),
        "maintainer_translated": {
            "en" : "Land Information Ontario",
            "fr" : "Information sur les terres de l'Ontario"
        },
        "maintainer_email": "lio@ontario.ca",
        "access_level": "open",
        "resources": build_resources(dcat_dict['distribution'],
                                     identifier_from_url(dcat_dict['identifier']),
                                     english_xml,
                                     dcat_dict['landingPage']),
        "update_frequency": "other",
        "exemption": "none",
        "exemption_rationale": {
            "en": "",
            "fr": ""
        },
        "name": ontario_theme_helpers.name_cleaner(dcat_dict["title"]),
        "private": False,
        "state": "active",
        "groups": [{'name': 'ontario-geohub'}] # optional
    } 

    if "rul" in package_dict['keywords']['en']:
        package_dict['access_level'] = "restricted"

    # get license
    license = get_license_from_xml(english_xml)

    geohub_update_frequency = extract_update_frequency(package_dict['notes_translated']['en'])
    if geohub_update_frequency:
        package_dict['update_frequency'] = update_frequencies[geohub_update_frequency]

    # get maintainer name and maintainer email
    geohub_contact_info = extract_contact_info(package_dict['notes_translated']['en'])
    if geohub_contact_info:
            geohub_fr_contact_info = extract_fr_contact_info(package_dict['notes_translated']['fr'])
            package_dict['maintainer_email'] = geohub_contact_info['maintainer_email']
            package_dict['maintainer_translated']['en'] = geohub_contact_info['maintainer_name']

            if "maintainer_branch" in geohub_contact_info:
                package_dict['maintainer_branch'] = {
                    'en' : geohub_contact_info['maintainer_branch']  
                }
            if geohub_fr_contact_info:
                package_dict['maintainer_translated']['fr'] = geohub_fr_contact_info['maintainer_name']
                if "maintainer_branch" in geohub_fr_contact_info:
                    package_dict['maintainer_branch']['fr'] = geohub_fr_contact_info['maintainer_branch']                
            else: 
                package_dict['maintainer_translated']['fr'] = package_dict['maintainer_translated']['en']
                
            if 'owner_org' not in package_dict and 'ministry' in geohub_contact_info:
                package_dict['owner_org'] = get_org_id(geohub_contact_info['ministry'])
    else:

        contact = extract_ontario_email(package_dict['notes_translated']['en'])
        if contact:
            package_dict['maintainer_email'] = contact.strip()
            if dcat_dict["contactPoint"]["fn"]:
                dcat_dict["contactPoint"]["fn"]
            elif package_dict['maintainer_email'].replace("@ontario.ca","").find(".") == -1:
                package_dict['maintainer_translated']['en'] = package_dict['maintainer_email'].replace("@ontario.ca","").strip()
            else:
                package_dict['maintainer_translated']['en'] = get_ontario_employee_name(package_dict['maintainer_email'])
            package_dict['maintainer_translated']['fr'] = package_dict['maintainer_translated']['en']


    # first, check whether the ministry is in the metadata
    ministry = get_ministry_from_xml(english_xml)
    if ministry:
        package_dict['owner_org'] = get_org_id(ministry) 
    # if it isn't there, look in the description for ministry names           
    if 'owner_org' not in package_dict:
        # extract ministry
        ministry = extract_ministry(package_dict['notes_translated']['en'], package_dict['maintainer_email'])
        if ministry:
            package_dict['owner_org'] = get_org_id(ministry)

    if 'owner_org' not in package_dict:
        package_dict['owner_org'] = get_org_id("natural-resources-and-forestry")


    log.info(package_dict['maintainer_email'])

    '''

    for distribution in dcat_dict.get('distribution', []):
        resource = {
            'name': distribution.get('title'),
            'description': distribution.get('description'),
            'url': distribution.get('downloadURL') or distribution.get('accessURL'),
            'format': distribution.get('format'),
        }

        if distribution.get('byteSize'):
            try:
                resource['size'] = int(distribution.get('byteSize'))
            except ValueError:
                pass
        package_dict['resources'].append(resource)
    '''
    return package_dict


def ontario_to_dcat(package_dict):

    dcat_dict = {}

    dcat_dict['title'] = package_dict.get('title')
    dcat_dict['description'] = package_dict.get('notes')
    dcat_dict['landingPage'] = package_dict.get('url')


    dcat_dict['keyword'] = []
    for tag in package_dict.get('tags', []):
        dcat_dict['keyword'].append(tag['name'])


    dcat_dict['publisher'] = {}

    for extra in package_dict.get('extras', []):
        if extra['key'] in ['dcat_issued', 'dcat_modified']:
            dcat_dict[extra['key'].replace('dcat_', '')] = extra['value']

        elif extra['key'] == 'language':
            dcat_dict['language'] = extra['value'].split(',')

        elif extra['key'] == 'dcat_publisher_name':
            dcat_dict['publisher']['name'] = extra['value']

        elif extra['key'] == 'dcat_publisher_email':
            dcat_dict['publisher']['mbox'] = extra['value']

        elif extra['key'] == 'guid':
            dcat_dict['identifier'] = extra['value']

    if not dcat_dict['publisher'].get('name') and package_dict.get('maintainer'):
        dcat_dict['publisher']['name'] = package_dict.get('maintainer')
        if package_dict.get('maintainer_email'):
            dcat_dict['publisher']['mbox'] = package_dict.get('maintainer_email')

    dcat_dict['distribution'] = []
    for resource in package_dict.get('resources', []):
        distribution = {
            'title': resource.get('name'),
            'description': resource.get('description'),
            'format': resource.get('format'),
            'byteSize': resource.get('size'),
            # TODO: downloadURL or accessURL depending on resource type?
            'accessURL': resource.get('url'),
        }
        dcat_dict['distribution'].append(distribution)

    return dcat_dict
