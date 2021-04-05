##############################################
#
# This should be done only from tst/prd server
#
###############################################


ver="1.8.43"

datarelease="1.8.24"

html_root=/var/www/
wrk_dir="/home/rykahsay/glygen-backend-api/"
server=$1

if [ -z "$server" ]
then
    echo ""
    echo "no server speficified!"
    echo ""
    exit
fi

if [ "$2" ]
then
    html_root=$2
fi

api_cgi_dir="$html_root/cgi-bin/api/"
api_html_dir="$html_root/html/api/"
common_html_dir="/var/www/html/common/"
db_name="glydb"
host="api.$server.glygen.org"

if [ $server == 'beta' ]
then
    api_cgi_dir="$html_root/cgi-bin/beta/api/"
    api_html_dir="$html_root/html/beta/api/"
    common_html_dir="/var/www/html/beta/common/"
    db_name="glydb_beta"
    host="beta-api.glygen.org"
fi


if [ $server == 'prd' ]
then
    host="api.glygen.org"
fi



mkdir -p $api_cgi_dir
mkdir -p $api_html_dir
rm -rf $api_cgi_dir/*
rm -rf $api_html_dir/*

release_dir="/data/shared/glygen/releases/api/v-$ver/"
if [ $server == 'dev' ] || [ $server == 'tst' ] || [ $server == 'beta' ] || [ $server == 'prd' ]
then
    cp $release_dir/api-cgi.tar.gz $api_cgi_dir/
    cp $release_dir/api-html.tar.gz $api_html_dir/
else
    scp rykahsay@dev.glygen.org:$release_dir/api-cgi.tar.gz $api_cgi_dir/
    scp rykahsay@dev.glygen.org:$release_dir/api-html.tar.gz $api_html_dir/
fi


cd $api_cgi_dir/
tar xvfz api-cgi.tar.gz
rm -rf api-cgi.tar.gz

cd $api_html_dir
tar xvfz api-html.tar.gz
rm -rf api-html.tar.gz

#Change api host
sed -ri "0,/(\s*\"host\"\s*:).*$/{s/(\s*\"host\"\s*:).*$/\1\"$host\",/}" config.json


cd $wrk_dir
echo "Version v-$ver" > $api_cgi_dir/release-notes.txt
echo "Version v-$ver" > $api_html_dir/release-notes.txt

# set the server type in the config file
sed -ri "0,/(\s*\"server\"\s*:).*$/{s/(\s*\"server\"\s*:).*$/\1\"$server\"/}" $api_cgi_dir/conf/config.json
sed -ri "0,/(\s*\"moduleversion\"\s*:).*$/{s/(\s*\"moduleversion\"\s*:).*$/\1\"$ver\"/}" $api_cgi_dir/conf/config.json
sed -ri "0,/(\s*\"datarelease\"\s*:).*$/{s/(\s*\"datarelease\"\s*:).*$/\1\"$datarelease\"/}" $api_cgi_dir/conf/config.json



python upsert-version.py -d $db_name -v $ver -c api



cd $common_html_dir/images
rm watermark.png
ln -s $server-watermark.png watermark.png




#cd $wrk_dir
#python validate-responses-step1.py -s $server | grep STATUS


cd $wrk_dir
python update-search-init.py -s $server

