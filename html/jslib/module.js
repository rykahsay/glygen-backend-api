var resJson = {};
var pageId = 'home';
var htmlRoot = "";
var cgibin = "/cgi-bin";
var domainUrlDict = {};


////////////////////////////////
$(document).ready(function() {

    var url = '/cgi-bin/init.py';
    var reqObj = new XMLHttpRequest();
    reqObj.open("POST", url, true);
    reqObj.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
    reqObj.onreadystatechange = function() {
        if (reqObj.readyState == 4 && reqObj.status == 200) {
            resJson = JSON.parse(reqObj.responseText);
            if(resJson["taskstatus"] != 1){
                $("#pagecn").html("<br><br>" + resJson["errormsg"]);
            }
            else{
                $("#moduleversioncn").html(resJson["moduleversion"]);
                domainUrlDict = resJson["domains"];
                setNavigation(resJson["domains"]);
            }
        }
    };
    var postData = '';
    reqObj.send(postData);

});



function setNavItemAsCurrent(itemText) {
     $('.nav > li > a').each(function () {
        if ($(this).text().indexOf(itemText) >= 0) {
                $(this).parent().addClass('current');
        }
    });
}


////////////////
function setNavigation(domainUrls){

    var url = window.location.href;
    var fullFilename = url.substring(url.lastIndexOf('/') + 1);
    var filename = fullFilename.substring(0, fullFilename.lastIndexOf('.'));
    var navItemText = filename.replace(/_/g, ' ').toUpperCase();
    //var domain = url.replace("data.", "").replace("-", "")
    var glygen_url = window.location.origin;
    if (glygen_url.indexOf('beta-') >= 0) {
        glygen_url = glygen_url.replace("beta-", "beta.");
    }
    if (glygen_url.indexOf('data.') >= 0) {
       glygen_url = glygen_url.replace("data.", "");
    } else if (glygen_url.indexOf('sparql.') >= 0) {
       glygen_url = glygen_url.replace("sparql.", "");
    }
   
   var domain = glygen_url + "/";
    
    if (navItemText == '') {
        navItemText = 'HOME';
    } else if (navItemText == 'INDEX') {
        navItemText = 'HOME';
    } else if (navItemText == 'CONTACT') {
        navItemText = 'HELP';
    } else if (navItemText == 'HOW TO CITE') {
        navItemText = 'HELP';
    } else if (navItemText == 'ABOUT') {
        navItemText = 'HELP';
    } else if (navItemText == 'RESOURCES') {
        navItemText = 'MORE';
    } else if (navItemText == 'MEDIA') {
        navItemText = 'MORE';
    } else if (navItemText == 'FRAMEWORKS') {
        navItemText = 'MORE';
    } else if (navItemText == 'GLYGEN SETTINGS') {
        navItemText = 'MY GLYGEN';
    }

    if (url.indexOf('data.') >= 0) {
        navItemText = 'DATA';
    } else if (url.indexOf('sparql.') >= 0) {
        navItemText = 'SPARQL';
    }
    else if (url.indexOf('api.') >= 0) {
        navItemText = 'API';
    }

    $('.nav > li').removeClass('current');
    setNavItemAsCurrent(navItemText);
    
    // for Data and SPARQL link in header page
    $("#a_portal").attr('href', domainUrls["portal"]);
    $("#a_data").attr('href', domainUrls["data"]);
    $("#a_api").attr('href', domainUrls["api"]);
    $("#a_sparql").attr('href', domainUrls["sparql"]);

    
    $.each($(".a_header"), function(i, v) {
        var nav_url = $(v).attr('href');
        $(v).attr('href', domain + nav_url);
    });


}


$(document).on('click', '.subdomain', function (event) {
    event.preventDefault();
    var k = this.id.split("_").pop();
    window.location.href = domainUrlDict[k];

});
