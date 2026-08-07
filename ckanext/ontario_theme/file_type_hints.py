# encoding: utf-8

from ckan.common import _

def get_file_type_hints():
    return {
        u'CSV': {
            u'heading': _(
                u'Comma-separated values (CSV)'
            ),
            u'body': [
                _(
                    u'This file stores data in a grid format, '
                    u'with rows and columns.'
                ),
                _(
                    u'Data is machine-readable. This means a computer can '
                    u'interpret it for data visualizations and deeper analysis.'
                ),
                _(
                    u'Access CSV files using a spreadsheet application, '
                    u'text editor or database.'
                ),
            ],
        },
        u'XLSX': {
            u'heading': _(
                u'Microsoft Excel (XLSX)'
            ),
            u'body': [
                _(
                    u'Microsoft’s spreadsheet file format. This file stores '
                    u'data in a digital grid and may include formatting such '
                    u'as colours, graphs and charts.'
                ),
                _(
                    u'Access XLSX files using any spreadsheet application.'
                ),
            ],
        },
        u'PDF': {
            u'heading': _(
                u'Portable Document Format (PDF)'
            ),
            u'body': [
                _(
                    u'A digital document that may include text, images and '
                    u'links. PDFs are useful for printing or sharing online.'
                ),
                _(
                    u'Access PDF files using a web browser, PDF reader or '
                    u'word processor.'
                ),
            ],
        },
        u'ZIP': {
            u'heading': _(
                u'ZIP'
            ),
            u'body': [
                _(
                    u'A ZIP is a closed—or “zipped”—folder that can hold one '
                    u'or more files (of any format type) and folders. ZIP '
                    u'files let you share many items as one bundle, instead '
                    u'of individual files.'
                ),
                _(
                    u'Access ZIP files with an unzipping software application. '
                    u'Some devices may unzip folders for you.'
                ),
            ],
        },
        u'DOCX': {
            u'heading': _(
                u'Microsoft Word (DOCX)'
            ),
            u'body': [
                _(
                    u'Microsoft’s word processing file format. These files '
                    u'may have text with styling (like colours or italics), '
                    u'images and graphs.'
                ),
                _(
                    u'Access DOC files using any word pressing application.'
                ),
            ],
        },
        u'DOC': {
            u'heading': _(
                u'Microsoft Word (DOC)'
            ),
            u'body': [
                _(
                    u'Microsoft’s older word processing file format. These '
                    u'files may contain text with styling (like colours or '
                    u'italics), images and graphs.'
                ),
                _(
                    u'Access DOC files using any word processing application.'
                ),
            ],
        },
        u'TXT': {
            u'heading': _(
                u'Text file (TXT)'
            ),
            u'body': [
                _(
                    u'A document format containing only text or numbers with '
                    u'no styling.'
                ),
                _(
                    u'Data is machine-readable. This means a computer can '
                    u'interpret it for data visualizations and deeper analysis.'
                ),
                _(
                    u'Access TXT files with any word processing or text '
                    u'editing application.'
                ),
            ],
        },
        u'WEB': {
            u'heading': _(
                u'Website links (WEB)'
            ),
            u'body': [
                _(
                    u'These are links to data published on the Internet '
                    u'outside the Data Catalogue.'
                ),
                _(
                    u'Access web links using any web browser connected to '
                    u'the Internet.'
                ),
            ],
        },
        u'XLS': {
            u'heading': _(
                u'Microsoft Excel (XLS)'
            ),
            u'body': [
                _(
                    u'An older version of Microsoft’s spreadsheet file '
                    u'format. This file stores data in a digital grid and '
                    u'may include formatting such as colours, graphs and '
                    u'charts.'
                ),
                _(
                    u'Access XLS files using any spreadsheet application.'
                ),
            ],
        },
        u'KML': {
            u'heading': _(
                u'Keyhole Markup Language (KML)'
            ),
            u'body': [
                _(
                    u'KML files store geographic data that you can see on '
                    u'a map. An example might be data about a park, like '
                    u'its boundaries and the types of trees you can find '
                    u'in it.'
                ),
                _(
                    u'Data is machine-readable. This means a computer can '
                    u'interpret it for data visualizations and deeper analysis.'
                ),
                _(
                    u'Access KML files with any mapping application.'
                ),
            ],
        },
        u'SHP': {
            u'heading': _(
                u'Shapefile (SHP)'
            ),
            u'body': [
                _(
                    u'A digital map file that stores information about '
                    u'specific locations or areas on a map.'
                ),
                _(
                    u'Access SHP files with any geographic information '
                    u'system (GIS) application.'
                ),
            ],
        },
        u'JSON': {
            u'heading': _(
                u'JavaScript Object Notation (JSON)'
            ),
            u'body': [
                _(
                    u'JSON files use key-value pairs to store data in a '
                    u'text format.'
                ),
                _(
                    u'Data is machine-readable. This means a computer can '
                    u'interpret it for data visualizations and deeper analysis.'
                ),
                _(
                    u'Access JSON files using any text editing or code-based '
                    u'application.'
                ),
            ],
        },
        u'MDB': {
            u'heading': _(
                u'Microsoft Access (MDB)'
            ),
            u'body': [
                _(
                    u'Microsoft’s database file format. These files store '
                    u'and combine information from multiple different files.'
                ),
                _(
                    u'Access MDB files with Microsoft Access, or convert it '
                    u'to CSV or TXT.'
                ),
            ],
        },
        u'DBF': {
            u'heading': _(
                u'dBase (DBF)'
            ),
            u'body': [
                _(
                    u'A database file format used to store structured data '
                    u'in tables with rows and columns.'
                ),
                _(
                    u'Data can be accessed and managed using database '
                    u'applications or converted to other formats such as '
                    u'CSV for analysis.'
                ),
            ],
        },
        u'GEOJSON': {
            u'heading': _(
                u'Geographic JavaScript Object Notation (GeoJSON)'
            ),
            u'body': [
                _(
                    u'A digital map file that stores information about '
                    u'specific locations or areas on a map.'
                ),
                _(
                    u'Data is machine-readable. This means a computer can '
                    u'interpret it for data visualizations and deeper analysis.'
                ),
                _(
                    u'Access GeoJSON files with any mapping application.'
                ),
            ],
        },
        u'GEOTIFF': {
            u'heading': _(
                u'GeoTIFF (GEOTIFF)'
            ),
            u'body': [
                _(
                    u'A digital map file that stores geographic information '
                    u'along with image data, such as satellite imagery or '
                    u'aerial photographs.'
                ),
                _(
                    u'Data is machine-readable. This means a computer can '
                    u'interpret the file for mapping, visualization and '
                    u'deeper analysis.'
                ),
                _(
                    u'Access GeoTIFF files with geographic information '
                    u'system (GIS) or image viewing applications.'
                ),
            ],
        },
        u'TSV': {
            u'heading': _(
                u'Tab-separated values (TSV)'
            ),
            u'body': [
                _(
                    u'This file stores data in a grid format, with rows and '
                    u'columns. Values are separated by tabs instead of commas.'
                ),
                _(
                    u'Data is machine-readable. This means a computer can '
                    u'interpret the file for data visualizations and deeper '
                    u'analysis.'
                ),
                _(
                    u'Access TSV files using a spreadsheet application, '
                    u'text editor or database.'
                ),
            ],
        },
        u'XML': {
            u'heading': _(
                u'Extensible Markup Language (XML)'
            ),
            u'body': [
                _(
                    u'XML files provide information about a specific '
                    u'location, like average rainfall or the number of '
                    u'owls seen.'
                ),
                _(
                    u'Data is machine-readable. This means a computer can '
                    u'interpret it for data visualizations and deeper analysis.'
                ),
                _(
                    u'Access XML files with any mapping application.'
                ),
            ],
        },
    }


def get_file_type_hint(file_format):
    normalized_format = (file_format or u'').strip().upper()
    return get_file_type_hints().get(normalized_format)
