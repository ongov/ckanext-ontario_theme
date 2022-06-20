#! /bin/bash

# function to convert a string into a Sed escaped string.
# This string can be used in sed replace command.
# arguments: 1 String to be modified with escape chars
# return: Modified String with escape chars
# example:
#   ret = `str_to_sed_str "input string"`
function str_to_sed_str(){
        sed_str=$(sed 's/[&/\]/\\&/g' <<<$@)
        echo $sed_str
}

# replaces a given string with the replacement string inside
# ckan.ini file. ckan.ini file assumed to be at $CKANINIPATH
# arguments: string needing replacement, string replaced by
# return: none
# example:
#    replace_str_in_ckan_ini "replace this" "by this"
function replace_str_in_ckan_ini() {
    ORIGINAL_STR = "$1"
    REPLACEMENT_STR = "$2"
    sed -i -r 's/'"$ORIGINAL_STR"'/'"$REPLACEMENT_STR"'/' $CKANINIPATH
}