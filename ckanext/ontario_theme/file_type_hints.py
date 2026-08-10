# encoding: utf-8

from ckan.common import _

def get_file_type_hints():

    return {
        u'CSV': {
            u'heading': _(u'Comma-separated values (CSV)'),
            u'body': [
                _(u'This file stores data in a grid format, with rows and columns.'),
                _(u'Data is machine-readable. This means a computer can interpret it for data visualizations and deeper analysis.'),
                _(u'Access CSV files using a spreadsheet application, text editor or database.'),
            ],
        },
        u'XLSX': {
            u'heading': _(u'Microsoft Excel (XLSX)'),
            u'body': [
                _(u'Microsoft’s spreadsheet file format. This file stores data in a digital grid and may include formatting such as colours, graphs and charts.'),
                _(u'Access XLSX files using any spreadsheet application.'),
            ],
        },
        u'PDF': {
            u'heading': _(u'Portable Document Format (PDF)'),
            u'body': [
                _(u'A digital document that may include text, images and links. PDFs are useful for printing or sharing online.'),
                _(u'Access PDF files using a web browser, PDF reader or word processor.'),
            ],
        },
        u'ZIP': {
            u'heading': _(u'ZIP'),
            u'body': [
                _(u'A ZIP is a closed—or “zipped”—  folder that can hold one or more files (of any format type) and folders. ZIP files let you share many items as one bundle, instead of individual files.'),
                _(u'Access ZIP files with an unzipping software application. Some devices may unzip folders for you.'),
            ],
        },
        u'DOCX': {
            u'heading': _(u'Microsoft Word (DOCX)'),
            u'body': [
                _(u'Microsoft’s word processing file format. These files may have text with styling (like colours or italics), images and graphs.'),
                _(u'Access DOCX files using any word processing application.'),
            ],
        },
        u'TXT': {
            u'heading': _(u'Text file (TXT'),
            u'body': [
                _(u'A document format containing only text or numbers with no styling.'),
                _(u'Data is machine-readable. This means a computer can interpret it for data visualizations and deeper analysis.'),
                _(u'Access TXT files with any word processing or text editing application.'),
            ],
        },
        u'WEB': {
            u'heading': _(u'Website links (WEB)'),
            u'body': [
                _(u'These are links to data published on the Internet outside the Data Catalogue.'),
                _(u'Access web links using any web browser connected to the Internet.'),
            ],
        },
        u'XLS': {
            u'heading': _(u'Microsoft Excel (XLS)'),
            u'body': [
                _(u'An older version of Microsoft’s spreadsheet file format. This file stores data in a digital grid and may include formatting such as colours, graphs and charts.'),
                _(u'Access XLS files using any spreadsheet application.'),
            ],
        },
        u'KML': {
            u'heading': _(u'Keyhole Markup Language (KML)'),
            u'body': [
                _(u'KML files store geographic data that you can see on a map. An example might be data about a park, like its boundaries and the types of trees you can find in it.'),
                _(u'Data is machine-readable. This means a computer can interpret it for data visualizations and deeper analysis.'),
                _(u'Access KML files with any mapping application.'),
            ],
        },
        u'SHP': {
            u'heading': _(u'Shapefile (SHP)'),
            u'body': [
                _(u'A digital map file that stores information about specific locations or areas on a map.'),
                _(u'Access SHP files with any geographic information system (GIS) application.'),
            ],
        },
        u'JSON': {
            u'heading': _(u'JavaScript Object Notation (JSON)'),
            u'body': [
                _(u'JSON files use key-value pairs to store data in a text format.'),
                _(u'Data is machine-readable. This means a computer can interpret it for data visualizations and deeper analysis.'),
                _(u'Access JSON files using any text editing or code-based application.'),
            ],
        },
        u'MDB': {
            u'heading': _(u'Microsoft Access (MDB)'),
            u'body': [
                _(u'Microsoft’s database file format. These files store and combine information from multiple different files.'),
                _(u'Access MDB files with Microsoft Access, or convert it to CSV or TXT.'),
            ],
        },
        u'GEOJSON': {
            u'heading': _(u'Geographic JavaScript Object Notation (GeoJSON)'),
            u'body': [
                _(u'A digital map file that stores information about specific locations or areas on a map.'),
                _(u'Data is machine-readable. This means a computer can interpret it for data visualizations and deeper analysis.'),
                _(u'Access GeoJSON files with any mapping application.'),
            ],
        },
        u'XML': {
            u'heading': _(u'Extensible Markup Language (XML)'),
            u'body': [
                _(u'XML files provide information about a specific location, like average rainfall or the number of owls seen.'),
                _(u'Data is machine-readable. This means a computer can interpret it for data visualizations and deeper analysis.'),
                _(u'Access XML files with any mapping application.'),
            ],
        },
        u'dBase': {
            u'heading': _(u'dBase (DBF)'),
            u'body': [
                _(u'A database file format used to store structured data in tables with rows and columns.'),
                _(u'Data can be accessed and managed using database applications or converted to other formats such as CSV for analysis.'),
            ],
        },
        u'DOC': {
            u'heading': _(u'Microsoft Word (DOC)'),
            u'body': [
                _(u'Microsoft’s older word processing file format. These files may contain text with styling (like colours or italics), images and graphs.'),
                _(u'Access DOC files using any word processing application.'),
            ],
        },
        u'GEOTIFF': {
            u'heading': _(u'GeoTIFF (GEOTIFF)'),
            u'body': [
                _(u'A digital map file that stores geographic information along with image data, such as satellite imagery or aerial photographs.'),
                _(u'Data is machine-readable. This means a computer can interpret the file for mapping, visualization and deeper analysis.'),
                _(u'Access GeoTIFF files with geographic information system (GIS) or image viewing applications.'),
            ],
        },
        u'TSV': {
            u'heading': _(u'Tab-separated values (TSV)'),
            u'body': [
                _(u'This file stores data in a grid format, with rows and columns. Values are separated by tabs instead of commas.'),
                _(u'Data is machine-readable. This means a computer can interpret the file for data visualizations and deeper analysis.'),
                _(u'Access TSV files using a spreadsheet application, text editor or database.'),
            ],
        },
    }

def get_file_type_hint(file_format):
    normalized_format = (file_format or u'').strip().upper()
    return get_file_type_hints().get(normalized_format)
