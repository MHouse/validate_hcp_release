#! /usr/bin/env python
__author__ = 'mhouse01'

import requests
import json
import os
import csv
from lxml import etree
from sys import exit
from operator import itemgetter, attrgetter
import argparse
import ConfigParser
from seriesDetails import seriesDetails, csvOrder, seriesLabels, scanIsPackage

# Declare the XNAT Namespace for use in XML parsing
xnatNS = "{http://nrg.wustl.edu/xnat}"
xmlFormat =  {'format': 'xml'}
jsonFormat = {'format': 'json'}

# PARSE INPUT
parser = argparse.ArgumentParser(description="Alpha program to pull Subject session parameters from XNAT for verification")

parser.add_argument("-c", "--config", dest="configFile", default="validate_hcp_release.cfg", type=str, help="config file must be specified")
parser.add_argument("-P", "--project", dest="Project", default="HCP_Phase2", type=str, help="specify project")
parser.add_argument("-S", "--subject", dest="Subject", type=str, help="specify subject of interest")
parser.add_argument("-D", "--destination_dir", dest="destDir", default='/tmp', type=str, help="specify the directory for output")
parser.add_argument("-M", "--output_map", dest="outputMap", default='all', type=str, help="specify the output mapping: all, public, package")
parser.add_argument("-v", "--verbose", dest="verbose", default=False, action="store_true", help="show more verbose output")
parser.add_argument('--version', action='version', version='%(prog)s: v0.1')

args = parser.parse_args()
args.destDir = os.path.normpath( args.destDir )

# Read the config file
config = ConfigParser.ConfigParser()
try:
    config.read( args.configFile )
    username = config.get('Credentials', 'username')
    password = config.get('Credentials', 'password')
    restServerName = config.get('Server', 'server')
    restSecurity = config.getboolean('Server', 'security')
except ConfigParser.Error as e:
    print "Error reading configuration file:"
    print "    " + str( e )
    exit(1)

if restSecurity:
    print "Using only secure connections"
    restRoot = "https://" + restServerName
else:
    print "Security turned off for all connections"
    restRoot = "http://" + restServerName + ":8080"

# If we find an OS certificate bundle, use it instead of the built-in bundle
if requests.utils.get_os_ca_bundle_path() and restSecurity:
    os.environ['REQUESTS_CA_BUNDLE'] = requests.utils.get_os_ca_bundle_path()
    print "Using CA Bundle: %s" % requests.utils.DEFAULT_CA_BUNDLE_PATH

# Establish a Session ID
try:
    r = requests.get( restRoot + "/data/JSESSION", auth=(username, password) )
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
restExperimentsURL = restRoot + "/data/archive/projects/" + args.Project + "/subjects/" + args.Subject + "/experiments/"
# Get the list of MR Sessions for the Subject in JSON format
try:
    # Create a dictionary of parameters for the rest call
    restParams = mrSessions.copy()
    restParams.update(jsonFormat)
    # Make the rest call
    r = requests.get( restExperimentsURL, params=restParams, headers=restSessionHeader)
    # If we don't get an OK; code: requests.codes.ok
    r.raise_for_status()
# Check if the REST Request fails
except (requests.ConnectionError, requests.exceptions.RequestException) as e:
    print "Failed to retrieve MR Session list: %s" % e
    exit(1)
# Parse the JSON from the GET
experimentJSON = json.loads( r.content )
# Strip off the trash that comes back with it and store it as a list of name/value pairs
experimentResultsJSON = experimentJSON.get('ResultSet').get('Result')
# List Comprehensions Rock!  http://docs.python.org/tutorial/datastructures.html
# Create a stripped down version of the results with a new field for seriesList; Store it in the experimentResults object
experimentResults = [ {'label': experimentItem.get('label').encode('ascii', 'ignore'),
                       'date':  experimentItem.get('date').encode('ascii', 'ignore'),
                       'subjectSessionNum': None,
                       'seriesList': None } for experimentItem in experimentResultsJSON ]

# Loop over the MR Experiment Results
for experiment in experimentResults:
    print "Gathering results for " + experiment['label']
    # Compose a rest URL for this Experiment
    restSingleExperimentURL = restExperimentsURL + experiment['label']
    # Make a rest request to get the complete XNAT Session XML
    try:
        r = requests.get( restSingleExperimentURL, params=xmlFormat, headers=restSessionHeader, timeout=10.0 )
        # If we don't get an OK; code: requests.codes.ok
        r.raise_for_status()
    # Check if the REST Request fails
    except requests.Timeout as e:
        print "Timed out while attempting to retrieve XML:"
        print "    " + str( e )
        if not args.restSecurity:
            print "Note that insecure connections are only allowed locally"
        exit(1)
    # Check if the REST Request fails
    except (requests.ConnectionError, requests.exceptions.RequestException) as e:
        print "Failed to retrieve XML: %s" % e
        exit(1)

    # Parse the XML result into an Element Tree
    root = etree.fromstring(r.text.encode(r.encoding))
    # Extract the Study Date for the session
    if experiment['date'] == "":
        experiment['date'] = "2013-01-01"
    print "Assuming study date of " + experiment['date']

    # Start with an empty series list
    seriesList = list()

    # Iterate over 'scan' records that contain an 'ID' element
    for element in root.iterfind(".//" + xnatNS + "scan[@ID]"):
        # Create an empty seriesDetails record
        currentSeries = seriesDetails()
        #Record some basic experiment level info in each scan
        currentSeries.subjectName = args.Subject
        currentSeries.sessionLabel = experiment['label']
        currentSeries.sessionDate = experiment['date']
        currentSeries.fromScanXML( element )
        # Add the current series to the end of the list
        seriesList.append( currentSeries )
    # Sort the series list by DateTime
    seriesList.sort( key=attrgetter('DateTime') )
    # Store the subjectSessionNum extracted from the first item (first acquired scan) in the sorted list
    experiment['subjectSessionNum'] = iter(seriesList).next().subjectSessionNum
    # Store the series list along with the experiment label
    experiment['seriesList'] = seriesList

# Sort the Experiment Results list by the Subject Session Number
experimentResults.sort( key=itemgetter('subjectSessionNum') )

# Name the CSV file by the Subject name
csvFile = args.destDir + os.sep + args.Subject + "_" + args.outputMap + ".csv"
# Create an empty Series Notes object.  This can be populated with field specific notes for each Experiment
seriesNotes = seriesDetails()
# Open the CSV file for write/binary
with open( csvFile, 'wb' ) as f:
    # Create a CSV Writer for dictionary formatted objects.  Give it the Dictionary order for output.
    csvWriter = csv.DictWriter( f, csvOrder( args.outputMap ) )
    # Write out the series labels as a Header
    if args.outputMap != "package":
        csvWriter.writerow( seriesLabels(args.outputMap) )
    # Loop over all experiment results
    for experiment in experimentResults:
        # Populate the Series Notes for this Experiment with the Experiment Date and Label
        seriesNotes.scan_ID = experiment['label']
        seriesNotes.startTime = experiment['date']
        # Write out the notes only on 'all' maps
        if args.outputMap == "all":
            csvWriter.writerow( seriesNotes.asDictionary(args.outputMap) )
        # Loop over all scans in each experiment
        for scan in experiment['seriesList']:
            # Write each scan by converting it to a Dictionary and pulling the relevant Mapping subset
            nextRow = scan.asDictionary(args.outputMap)
            # But only if this row should be included
            if args.outputMap == "all" or \
                (args.outputMap == "release" and scan.targetForRelease == "1") or \
                (args.outputMap == "release" and restServerName == "hcpx-demo.humanconnectome.org") or \
                (args.outputMap == "package" and scanIsPackage(scan.dbDesc)):
                csvWriter.writerow( nextRow )

print "Subject details written to: " + csvFile
