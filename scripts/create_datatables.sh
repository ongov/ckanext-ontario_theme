# create datatables when ckan and postgres are both installed

#export SUDOPASS='1'

ckan -c /etc/ckan/default/ckan.ini db init
output=`echo $SUDOPASS | sudo -S -k -u postgres psql -c "SELECT table_name FROM information_schema.tables"`
# TODO:output should have '194' as the number of tables

