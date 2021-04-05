usage()
{
	echo "Sets the API root URL in API test files in this directory. Run this before running deployment script"
        echo "usage:	./set_api_root API_URL"
	echo ""
	echo ""
        echo "examples:    ./set_api_root '/api'"
        echo "             ./set_api_root 'https://glygen.ccrc.uga.edu/glygen/api'"
        exit 3
}

if [ "$1" == "--help" ] || [ -z "$1" ]; then
    usage; exit 0
fi

api_url=$1

# set htmlRoot to 
sed -ri "s/^(var\s*htmlRoot\s*=\s*).*/\1'${api_url//\//\\/}';/" html/test/*.html
