#! /usr/bin/env python
__author__ = 'mhouse01'

import requests
import re
import urllib2
import json
import shutil
import os
from datetime import datetime
from lxml import etree
from sys import exit
from operator import attrgetter
import argparse
import ConfigParser
# TODO Will be switching to 'ConfigParser' for config file
# If you have an object x, and a file object f that's been opened for writing, the simplest way to pickle the object is:
# pickle.dump(x, f)
# To unpickle the object again, if f is a file object which has been opened for reading:
# x = pickle.load(f)
from Matt_PW import importUsername, importPassword

# Declare the XNAT Namespace for use in XML parsing
xnatNS = "{http://nrg.wustl.edu/xnat}"
xmlFormat =  {'format': 'xml'}
jsonFormat = {'format': 'json'}
csvOrder = [
    'startTime',
    'scan_ID',
    'scan_type',
    'series_description',
    'quality',
    'subjectSessionNum',
    'releaseCountScan',
    'targetForRelease',
    'dbID',
    'dbType',
    'params_shimGroup',
    'params_biasGroup',
    'seFieldMapGroup',
    'params_geFieldMapGroup',
    'dbDesc',
    'params_peRotation',
    'params_peSwap',
    'params_peDirection',
    'params_eprimeScriptNum' ]
seriesLabels = dict(
    startTime = "Acquisition Time",
    scan_ID = "IDB_scan",
    scan_type = "IDB_Type",
    series_description = "IDB_Description",
    quality = "Usability",
    subjectSessionNum = "Session",
    releaseCountScan = "CountScan",
    targetForRelease = "Release",
    dbID = "CDB_scan",
    dbType = "CDB_Type",
    params_shimGroup = "Shim Group",
    params_biasGroup = "BiasField group",
    seFieldMapGroup = "SE_FieldMap group",
    params_geFieldMapGroup = "GE_FieldMap group",
    dbDesc = "CDB_Description",
    params_peRotation = "PE Rotation",
    params_peSwap = "PE swap",
    params_peDirection = "PE direction",
    params_eprimeScriptNum = "E-Prime Script" )

class seriesDetails:
    """A simple class to store information about a scan series"""
    def __init__(self):
        self.startTime = None
        self.scan_ID = None
        self.scan_type = None
        self.series_description = None
        self.quality = None
        self.subjectSessionNum = None
        self.releaseCountScan = None
        self.targetForRelease = None
        self.dbID = None
        self.dbType = None
        self.params_shimGroup = None
        self.params_biasGroup = None
        self.seFieldMapGroup = None
        self.params_geFieldMapGroup = None
        self.dbDesc = None
        self.params_peRotation = None
        self.params_peSwap = None
        self.params_peDirection = None
        self.params_eprimeScriptNum = None
    def __repr__(self):
        return "<scan_ID:%s series_description:%s>" % (self.scan_ID, self.series_description)
    def asDictionary(self):
        detailsDict = dict(
            startTime = self.startTime,
            scan_ID = self.scan_ID,
            scan_type = self.scan_type,
            series_description = self.series_description,
            quality = self.quality,
            subjectSessionNum = self.subjectSessionNum,
            releaseCountScan = self.releaseCountScan,
            targetForRelease = self.targetForRelease,
            dbID = self.dbID,
            dbType = self.dbType,
            params_shimGroup = self.params_shimGroup,
            params_biasGroup = self.params_biasGroup,
            seFieldMapGroup = self.seFieldMapGroup,
            params_geFieldMapGroup = self.params_geFieldMapGroup,
            dbDesc = self.dbDesc,
            params_peRotation = self.params_peRotation,
            params_peSwap = self.params_peSwap,
            params_peDirection = self.params_peDirection,
            params_eprimeScriptNum = self.params_eprimeScriptNum )
        return detailsDict

#===============================================================================
# PARSE INPUT
#===============================================================================
parser = argparse.ArgumentParser(description="Alpha program to pull NIFTI data from XNAT and package it for FTP distribution")

parser.add_argument("-W", "--server", dest="restServerName", default="intradb.humanconnectome.org", type=str, help="specify which server to connect to")
parser.add_argument("-i", "--insecure", dest="restSecurity", default=True, action="store_false", help="specify whether to use security")

parser.add_argument("-c", "--config", dest="configFile", default="package_hcp_ftp.cfg", type=str, help="config file must be specified")
parser.add_argument("-u", "--username", dest="restUser", type=str, help="username must be specified")
parser.add_argument("-p", "--password", dest="restPass", type=str, help="password must be specified")

parser.add_argument("-P", "--project", dest="inputProject", default="HCP_Phase2", type=str, help="specify project")
parser.add_argument("-S", "--subject", dest="inputSubject", type=str, help="specify subject of interest")
parser.add_argument("-E", "--experiment", dest="inputExperiment", default="strc", type=str, help="specify experiment type of interest")

parser.add_argument("-D", "--destination_dir", dest="destDir", default='/tmp', type=str, help="specify the directory for output")
parser.add_argument("-l", "--list", dest="listOnly", default=False, action="store_true", help="only list files that would be retrieved")
parser.add_argument("-v", "--verbose", dest="verbose", default=False, action="store_true", help="show more verbose output")

parser.add_argument('--version', action='version', version='%(prog)s: v0.1')

args = parser.parse_args()

restServerName = args.restServerName
restSecurity = args.restSecurity
# TODO Need to switch back to command line arguments
configFile = args.configFile

username = importUsername
#username = args.restUser
password = importPassword
#password = args.restPass

project = args.inputProject
subject = args.inputSubject
experiment = subject + "_" + args.inputExperiment

destDir = os.path.normpath( args.destDir )
listOnly = args.listOnly
Verbose = args.verbose

restInsecureRoot = "http://" + restServerName + ":8080"
restSecureRoot = "https://" + restServerName
if restSecurity:
    print "Using only secure connections"
    restSelectedRoot = restSecureRoot
else:
    print "Security turned off for all connections"
    restSelectedRoot = restInsecureRoot

# If we find an OS certificate bundle, use it instead of the built-in bundle
if requests.utils.get_os_ca_bundle_path() and restSecurity:
    os.environ['REQUESTS_CA_BUNDLE'] = requests.utils.get_os_ca_bundle_path()
    print "Using CA Bundle: %s" % requests.utils.DEFAULT_CA_BUNDLE_PATH

# Establish a Session ID
try:
    r = requests.get( restSelectedRoot + "/data/JSESSION", auth=(username, password) )
    # If we don't get an OK; code: requests.codes.ok
    r.raise_for_status()
# Check if the REST Request fails
except (requests.ConnectionError, requests.exceptions.RequestException) as e:
    print "Failed to retrieve REST Session ID:"
    print "    " + str( e )
    exit(1)

restSessionID = r.content
print "Rest Session ID: %s " % (restSessionID)
restSessionHeader = {"Cookie": "JSESSIONID=" + restSessionID}
mrSessions = {"xsiType": "xnat:mrSessionData"}

# Get the list of MR Sessions for each Experiment
# Create a URL pointing to the Experiments for this Subject
restExperimentsURL = restSelectedRoot + "/data/archive/projects/" + project + "/subjects/" + subject + "/experiments/"
# Get the list of MR Sessions for the Subject in JSON format
try:
    restParams = mrSessions.copy()
    restParams.update(jsonFormat)
    r = requests.get( restExperimentsURL, params=restParams, headers=restSessionHeader)
    # If we don't get an OK; code: requests.codes.ok
    r.raise_for_status()
# Check if the REST Request fails
except (requests.ConnectionError, requests.exceptions.RequestException) as e:
    print "Failed to retrieve REST Series NIFTI: %s" % e
    exit(1)
# Parse the JSON from the GET
seriesJSON = json.loads( r.content )
# Strip off the trash that comes back with it and store it as a list of name/value pairs
experimentResultsJSON = seriesJSON.get('ResultSet').get('Result')
# List Comprehensions Rock!  http://docs.python.org/tutorial/datastructures.html
# Create a stripped down version of the results with a new field for seriesList; Store it in the experimentResults object
experimentResults = [ {'label': experimentItem.get('label').encode('ascii', 'ignore'), 'seriesList': None }
                      for experimentItem in experimentResultsJSON ]

for experiment in experimentResults:
    print "Gathering results for " + experiment['label']

    # Compose a rest URL for this Experiment
    restExperimentURL = restSelectedRoot + "/data/archive/projects/" + project + "/subjects/" + subject + "/experiments/" + experiment['label']
    # Make a rest request to get the complete XNAT Session XML
    try:
        r = requests.get( restExperimentURL, params=xmlFormat, headers=restSessionHeader, timeout=10.0 )
        # If we don't get an OK; code: requests.codes.ok
        r.raise_for_status()
    # Check if the REST Request fails
    except (requests.Timeout) as e:
        print "Timed out while attempting to retrieve XML:"
        print "    " + str( e )
        if not restSecurity:
            print "Note that insecure connections are only allowed locally"
        exit(1)
    # Check if the REST Request fails
    except (requests.ConnectionError, requests.exceptions.RequestException) as e:
        print "Failed to retrieve XML: %s" % e
        exit(1)

    # Parse the XML result into an Element Tree
    root = etree.fromstring(r.text.encode(r.encoding))
    # Extract the Study Date for the session
    studyDate = root.find(".//" + xnatNS + "date").text
    print "Assuming study date of " + studyDate

    # Start with an empty series list
    seriesList = list()

    # Iterate over 'scan' records that contain an 'ID' element
    for element in root.iterfind(".//" + xnatNS + "scan[@ID]"):
        # Create an empty seriesDetails record
        currentSeries = seriesDetails()
        #startTime = "Acquisition Time",
        currentSeries.startTime = element.findtext(".//" + xnatNS + "startTime")
        #scan_ID = "IDB_scan",
        currentSeries.scan_ID = int (element.get("ID") )
        #scan_type = "IDB_Type",
        currentSeries.scan_type = element.get("type")
        #series_description = "IDB_Description",
        currentSeries.series_description = element.findtext(".//" + xnatNS + "series_description")
        #quality = "Usability",
        currentSeries.quality = element.findtext(".//" + xnatNS + "quality")
        #subjectSessionNum = "Session",
        currentSeries.subjectSessionNum = element.findtext(".//" + xnatNS + "subjectSessionNum")
        #releaseCountScan = "CountScan",
        currentSeries.releaseCountScan = element.findtext(".//" + xnatNS + "releaseCountScan")
        #targetForRelease = "Release",
        currentSeries.targetForRelease = element.findtext(".//" + xnatNS + "targetForRelease")
        #dbID = "CDB_scan",
        currentSeries.dbID = element.findtext(".//" + xnatNS + "dbID")
        #dbType = "CDB_Type",
        currentSeries.dbType = element.findtext(".//" + xnatNS + "dbType")
        #params_shimGroup = "Shim Group",
        currentSeries.params_shimGroup = element.findtext(".//" + xnatNS + "shimGroup")
        #params_biasGroup = "BiasField group",
        currentSeries.params_biasGroup = element.findtext(".//" + xnatNS + "biasGroup")
        #seFieldMapGroup = "SE_FieldMap group",
        currentSeries.seFieldMapGroup = element.findtext(".//" + xnatNS + "seFieldMapGroup")
        #params_geFieldMapGroup = "GE_FieldMap group",
        currentSeries.params_biasGroup = element.findtext(".//" + xnatNS + "biasGroup")
        #dbDesc = "CDB_Description",
        currentSeries.dbDesc = element.findtext(".//" + xnatNS + "dbDesc")
        #params_peRotation = "PE Rotation",
        currentSeries.params_peRotation = element.findtext(".//" + xnatNS + "peRotation")
        #params_peSwap = "PE swap",
        currentSeries.params_peSwap = element.findtext(".//" + xnatNS + "peSwap")
        #params_peDirection = "PE direction",
        currentSeries.params_peDirection = element.findtext(".//" + xnatNS + "peDirection")
        #params_eprimeScriptNum = "E-Prime Script"
        currentSeries.params_eprimeScriptNum = element.findtext(".//" + xnatNS + "eprimeScriptNum")
        # Record the series Date and Time in
        #currentSeries.seriesDate = datetime.strptime(studyDate + " " + startTime, "%Y-%m-%d %H:%M:%S")
        # Add the current series to the end of the list
        seriesList.append(currentSeries)
    # Store the series list along with the experiment label
    experiment['seriesList'] = seriesList


import csv
with open('some.csv', 'wb') as f:
    writer = csv.DictWriter( f, csvOrder )
    writer.writerow( seriesLabels )
    # Loop over all experiment results
    for experiment in experimentResults:
        #writer.writerow( experiment['label'] )
        # Loop over all scans in each experiment
        for scan in experiment['seriesList']:
            writer.writerow( scan.asDictionary() )


print

#    print "Series %s, %s file(s) found; %s file(s) matching criteria" %\
#          ( item.seriesNum, len( fileResults ), len( fileResultsFiltered ) )

## De-Number Certain Scan Types
#specialCases = ["^T1w_MPR\d+$", "^T2w_SPC\d+$"]
## Create a regular expression search object
#searchRegex = re.compile( '|'.join(specialCases) )
## Iterate over the list of Series objects
#for item in seriesList:
#    # If the Series Name matches any of the special cases
#    reMatch = re.search( searchRegex, item.seriesDesc )
#    if reMatch:
#        # Strip the trailing digit from the series description
#        item.seriesDesc = re.sub( '\d+$', '', reMatch.group() )
#
## Create the filtered list; Exclude specified scan types from the list
#excludeList = ["Localizer", "AAHScout", "_old$", "^BIAS_(BC|32CH)", "^AFI", "^FieldMap_(Magnitude|Phase)"]
## Create a regular expression search object
#searchRegex = re.compile( '|'.join(excludeList) )
#
## Iterate over the list of Series objects
#for item in seriesList:
#    # if the scan quality is a 3 or greater and if the Instance Name does not match anything from the exclude list
#    if item.seriesQualityNumeric >= 3 and not re.search( searchRegex, item.seriesDesc ):
#        # Include the item in the final list
#        item.instanceIncluded = True
#    else:
#        # Exclude this item from the final list
#        item.instanceIncluded = False
#
## Filter the list by the instance inclusion flag
#seriesList = [item for item in seriesList if item.instanceIncluded]
#
## Sort by primary then secondary key (utilizes sorting stability)
#seriesList.sort( key=attrgetter('seriesDesc', 'seriesDate') )
#
## Make sure that the list is not empty
#if len(seriesList) > 0:
#    # The first one is always unique
#    seriesList[0].instanceNum = 1
#    seriesList[0].isUnique = True
## Make sure that the list has additional elements
#if len(seriesList) > 1:
#    # Start with the second item in the list
#    for i in range( 1, len(seriesList) ):
#        previousSeries = seriesList[i-1]
#        currentSeries = seriesList[i]
#        # Look for duplicate Series Descriptions, remembering that we have a sorted list
#        if previousSeries.seriesDesc != currentSeries.seriesDesc:
#            # This is unique because it's not the same as the previous one
#            currentSeries.instanceNum = 1
#            #currentSeries.instanceName = currentSeries.seriesDesc
#            currentSeries.isUnique = True
#        else:
#            # This is not unique
#            currentSeries.isUnique = False
#            # Neither is the previous one
#            previousSeries.isUnique = False
#            # Increment the current instance number
#            currentSeries.instanceNum = previousSeries.instanceNum + 1
#
## Tag Single Special Cases as not being unique
#specialCases = ["FieldMap_Magnitude", "FieldMap_Phase", "BOLD_RL_SB_SE", "BOLD_LR_SB_SE", "T1w_MPR", "T2w_SPC"]
## Iterate over the list of Series objects
#for item in seriesList:
#    # If the current Series Description matches one of our special cases
#    if item.seriesDesc in specialCases:
#        # Tag it as not unique
#        item.isUnique = False
#
## Re-sort by Series Number
#seriesList.sort( key=attrgetter('seriesNum') )
#
## Create instance names by re-numbering duplicates
#specialCases = ["T1w_MPR", "T2w_SPC"]
## Set the Instance Names
#for item in seriesList:
#    # For unique instances...
#    if item.isUnique:
#        # Just use the Series Description
#        item.instanceName = item.seriesDesc
#    # For non-unique instances...
#    elif item.seriesDesc in specialCases:
#        # Append the Series Description with the Instance Number
#        item.instanceName = item.seriesDesc + str(item.instanceNum)
#    else:
#        # Append the Series Description with an underscore and the Instance Number
#        item.instanceName = item.seriesDesc + "_" + str(item.instanceNum)
#
## Sanity Check. Verify that all Instance Names are unique
#instanceNames = [item.instanceName for item in seriesList]
## Compare the number of Series to the number of unique Instance Names
#if len(seriesList) == len( set(instanceNames) ):
#    print "Instance names verified as unique"
#else:
#    print "Instance names not unique."
#    exit(1)
#
## Create a tuple of the included resource types
#IncludedTypes = ('.nii.gz', '.bvec', '.bval')
## Get the actual list of file names and URLs for each series
#for item in seriesList:
#    # Create a URL pointing to the NIFTI resources for the series
#    niftiURL = restExperimentURL + "/scans/" + str( item.seriesNum) + "/resources/NIFTI/files"
#    # Get the list of NIFTI resources for the series in JSON format
#    try:
#        r = requests.get( niftiURL, params=jsonFormat, headers=restSessionHeader)
#        # If we don't get an OK; code: requests.codes.ok
#        r.raise_for_status()
#    # Check if the REST Request fails
#    except (requests.ConnectionError, requests.exceptions.RequestException) as e:
#        print "Failed to retrieve REST Series NIFTI: %s" % e
#        exit(1)
#    # Parse the JSON from the GET
#    seriesJSON = json.loads( r.content )
#    # Strip off the trash that comes back with it and store it as a list of name/value pairs
#    fileResults = seriesJSON.get('ResultSet').get('Result')
#    # List Comprehensions Rock!  http://docs.python.org/tutorial/datastructures.html
#    # Filter the File List to only include items where the URI ends with one of the defined file types
#    fileResultsFiltered = [ fileItem for fileItem in fileResults
#                            if fileItem.get('URI').endswith( IncludedTypes )]
#    # Let us know what was found and how many matched
#    print "Series %s, %s file(s) found; %s file(s) matching criteria" %\
#          ( item.seriesNum, len( fileResults ), len( fileResultsFiltered ) )
#    # Create a stripped down version of the results with a new field for FileName; Store it in the Series object
#    item.fileList = [ dict( zip( ('OriginalName', 'FileName', 'URI', 'Size'),
#        (fileItem.get('Name'), None, fileItem.get('URI'), long( fileItem.get('Size') ) ) ) )
#                      for fileItem in fileResultsFiltered ]
#    # Iterate across the individual files entries
#    for fileItem in item.fileList:
#        # Substitute the Instance Name in for the Series Description in File Names
#        # fileItem['FileName'] = fileItem.get('OriginalName').replace( item.seriesDescOrig, item.instanceName)
#        fileItem['FileName'] = re.sub( item.seriesDescOrig, item.instanceName, fileItem.get('OriginalName') )
#
## If we're not just listing the files
#if not listOnly:
#    # Make sure that the destination folder exists
#    if not os.path.exists( destDir ):
#        os.makedirs(destDir)
#    # Make a session specific folder
#    sessionFolder = destDir + os.sep + experiment
#    if not os.path.exists( sessionFolder ):
#        os.makedirs( sessionFolder )
#
## Inform the user that this will only list the files
#if listOnly:
#    print "Files will not be downloaded"
#
## Download the final filtered list
#for item in seriesList:
#    print "Series %s, Instance Name: %s, Included: %s" % (item.seriesNum, item.instanceName, item.instanceIncluded )
#    if item.instanceIncluded:
#        for fileItem in item.fileList:
#            # Get the current NIFTI resource in the series.
#            niftiURL = restSelectedRoot + fileItem.get('URI')
#            # List files only
#            if listOnly:
#                print "Would have downloaded %s..." % fileItem.get('FileName')
#                continue
#            # Create a Request object associated with the URL
#            niftiRequest = urllib2.Request( niftiURL )
#            # Add the Session Header to the Request
#            niftiRequest.add_header( "Cookie", restSessionHeader.get("Cookie") )
#            # Generate a fully qualified local filename to dump the data into
#            local_filename = destDir + os.sep + experiment + os.sep + fileItem.get('FileName')
#            print "Downloading %s..." % fileItem.get('FileName')
#            # Try to write the remote file to disk
#            try:
#                # Open a socket to the URL and get a file-like object handle
#                remote_fo = urllib2.urlopen( niftiRequest )
#                # Write the URL contents out to a file and make sure it gets closed
#                with open( local_filename, 'wb') as local_fo:
#                    shutil.copyfileobj( remote_fo, local_fo )
#            # If we fail to open the remote object, error out
#            except urllib2.URLError as e:
#                print e.args
#                exit(1)
#            # Get and print the local file size in MB
#            local_filesize = os.path.getsize(local_filename)
#            print "Local File Size: %0.1f MB;" % (local_filesize/(1024*1024.0)),
#            # Check that the downloaded file size matches the remote item
#            if fileItem.get('Size') == local_filesize:
#                print "Matches remote"
#            else:
#                print "Does not match remote!"
#                exit(1)
#
## Get a count of the number of files that should have been downloaded
#downloadCount = sum( [ len(item.fileList) for item in seriesList if item.instanceIncluded ] )
#print "Should have downloaded %s files" % downloadCount
#
## Pathing to find stuff in XNAT
## For lists, can append: ?format=json
## jsonFormat ={'format': 'json'}
## Projects:
##   https://intradb.humanconnectome.org/data/archive/projects
## Subjects:
##   https://intradb.humanconnectome.org/data/archive/projects/HCP_Phase2/subjects
## MR Sessions:
##   https://intradb.humanconnectome.org/data/archive/projects/HCP_Phase2/subjects/792564/experiments/?xsiType=xnat:mrSessionData
## Scans:
##   https://intradb.humanconnectome.org/data/archive/projects/HCP_Phase2/subjects/792564/experiments/792564_fnca/scans
## Scan XML:
##   https://intradb.humanconnectome.org/data/archive/projects/HCP_Phase2/subjects/792564/experiments/792564_fnca/scans/1
## Resources:
##   https://intradb.humanconnectome.org/data/archive/projects/HCP_Phase2/subjects/792564/experiments/792564_fnca/scans/1/resources
## Resource XML:
##   https://intradb.humanconnectome.org/data/archive/projects/HCP_Phase2/subjects/792564/experiments/792564_fnca/scans/1/resources/NIFTI
## Resource File List:
##   https://intradb.humanconnectome.org/data/archive/projects/HCP_Phase2/subjects/792564/experiments/792564_fnca/scans/1/resources/NIFTI/files
##
## URL Request Parameters
## payload = {'key1': 'value1', 'key2': 'value2'}
## r = requests.get("http://httpbin.org/get", params=payload)
## print r.url
## u'http://httpbin.org/get?key2=value2&key1=value1'
#
