##############################################
#
# This should be done only from dev server
#
###############################################
ver="v-1.8.44"

if [ ${HOSTNAME} != 'glygen-vm-dev' ]
then
    echo ""
    echo "This can only be done from glygen-vm-dev!"
    echo ""
    exit
fi

src_dir="/home/rykahsay/glygen-backend-api/"
release_dir="/data/shared/glygen/releases/api/$ver/"

if [ ! -d $release_dir ]; then
    mkdir $release_dir
fi
rm -rf $release_dir/*


cd $src_dir
f_list="idmapping supersearch mysite site auth commonquery data globalsearch glycan protein directsearch log misc motif pages typeahead usecases event"
for f in $f_list
do
   cp $f*.py $release_dir/
done

f_list="daemon-glycan daemon-protein errorlib util init libgly"
for f in $f_list
do
    cp $f.py $release_dir/
done

cp *.sh $release_dir/
cp *.cgi $release_dir/
cp -r conf $release_dir/
cp -r specs $release_dir/

cd $release_dir
tar cvfz api-cgi.tar.gz specs conf *.cgi *.py *.sh 
rm -rf $release_dir/*.cgi $release_dir/*.py $release_dir/conf

cd $src_dir/html
tar cvfz $release_dir/api-html.tar.gz * .htaccess





