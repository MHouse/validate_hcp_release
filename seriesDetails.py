__author__ = 'mhouse01'

import lxml
import re
from datetime import datetime
xnatNS = "{http://nrg.wustl.edu/xnat}"

def extractDict( d, keys ):
    return dict( (k, d[k]) for k in keys if k in d )

def numberToYN( numberYN ):
    textYN = None
    if numberYN is not None:
        if int(numberYN) == 0:
            textYN = 'N'
        else:
            textYN = 'Y'
    return textYN

def scanIsPackage( scanName ):
    if scanName is None:
        return None
    filterPackages = [
        'rfMRI_REST\d+_(RL|LR)$',
        'tfMRI_WM_(RL|LR)$',
        'tfMRI_GAMBLING_(RL|LR)$',
        'tfMRI_MOTOR_(RL|LR)$',
        'tfMRI_LANGUAGE_(RL|LR)$',
        'tfMRI_SOCIAL_(RL|LR)$',
        'tfMRI_RELATIONAL_(RL|LR)$',
        'tfMRI_EMOTION_(RL|LR)$' ]
    # Create a regular expression search object
    searchRegex = re.compile( '|'.join(filterPackages) )
    # If the Series Name matches any of the Functional Package names
    reMatch = re.search( searchRegex, scanName )
    return reMatch

class seriesDetails:
    """A simple class to store information about a scan series"""
    def __init__(self):
        self.subjectName = None
        self.sessionLabel = None
        self.sessionDate = None
        self.sessionDay = None
        self.startTime = None
        self.DateTime = None
        self.scan_ID = None
        self.scan_type = None
        self.series_description = None
        self.quality = None
        self.subjectSessionNum = None
        self.releaseCountScan = None
        self.targetForRelease = None
        self.dbID = None
        self.dbType = None
        self.viewScan = None
        self.params_shimGroup = None
        self.params_biasGroup = None
        self.seFieldMapGroup = None
        self.params_geFieldMapGroup = None
        self.dbDesc = None
        self.params_peDirection = None
        self.params_readoutDirection = None
        self.params_eprimeScriptNum = None
        self.scanOrder = None
        self.scanComplete = None
    def __repr__(self):
        return "<scan_ID:%s series_description:%s>" % (self.scan_ID, self.series_description)

    def fromScanXML(self, element):
        #sessionDay = "Session Day",
        self.sessionDay = element.findtext(".//" + xnatNS + "sessionDay")
        #startTime = "Acquisition Time",
        self.startTime = element.findtext(".//" + xnatNS + "startTime")
        #DateTime: Used only for sorting
        self.DateTime = datetime.strptime(self.sessionDate + " " + self.startTime, "%Y-%m-%d %H:%M:%S")
        #scan_ID = "IDB_scan",
        self.scan_ID = int (element.get("ID") )
        #scan_type = "IDB_Type",
        self.scan_type = element.get("type")
        #series_description = "IDB_Description",
        self.series_description = element.findtext(".//" + xnatNS + "series_description")
        #quality = "Usability",
        self.quality = element.findtext(".//" + xnatNS + "quality")
        #subjectSessionNum = "Session",
        self.subjectSessionNum = element.findtext(".//" + xnatNS + "subjectSessionNum")
        #releaseCountScan = "CountScan",
        self.releaseCountScan = element.findtext(".//" + xnatNS + "releaseCountScan")
        #targetForRelease = "Release",
        self.targetForRelease = element.findtext(".//" + xnatNS + "targetForRelease")
        #dbID = "CDB_scan",
        self.dbID = element.findtext(".//" + xnatNS + "dbID")
        #viewScan = "View",
        self.viewScan = element.findtext(".//" + xnatNS + "viewScan")
        #dbType = "CDB_Type",
        self.dbType = element.findtext(".//" + xnatNS + "dbType")
        #params_shimGroup = "Shim Group",
        self.params_shimGroup = element.findtext(".//" + xnatNS + "shimGroup")
        #params_biasGroup = "BiasField group",
        self.params_biasGroup = element.findtext(".//" + xnatNS + "biasGroup")
        #seFieldMapGroup = "SE_FieldMap group",
        self.seFieldMapGroup = element.findtext(".//" + xnatNS + "seFieldMapGroup")
        #params_geFieldMapGroup = "GE_FieldMap group",
        self.params_geFieldMapGroup = element.findtext(".//" + xnatNS + "geFieldMapGroup")
        #dbDesc = "CDB_Description",
        self.dbDesc = element.findtext(".//" + xnatNS + "dbDesc")
        #params_peDirection = "PE Direction",
        self.params_peDirection = element.findtext(".//" + xnatNS + "peDirection")
        #params_peDirection = "Readout Direction",
        self.params_readoutDirection = element.findtext(".//" + xnatNS + "readoutDirection")
        #params_eprimeScriptNum = "E-Prime Script"
        self.params_eprimeScriptNum = element.findtext(".//" + xnatNS + "eprimeScriptNum")
        #scanOrder = "Scan Order"
        self.scanOrder = element.findtext(".//" + xnatNS + "scanOrder")
        #scanOrder = "Scan Order"
        self.scanComplete = element.findtext(".//" + xnatNS + "scanComplete")

    def asDictionary(self, outputMap = 'all'):
        detailsDict = dict(
            subjectName = self.subjectName,
            sessionLabel = self.sessionLabel,
            sessionDay = self.sessionDay,
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
            viewScan = self.viewScan,
            params_shimGroup = self.params_shimGroup,
            params_biasGroup = self.params_biasGroup,
            seFieldMapGroup = self.seFieldMapGroup,
            params_geFieldMapGroup = self.params_geFieldMapGroup,
            dbDesc = self.dbDesc,
            params_peDirection = self.params_peDirection,
            params_readoutDirection = self.params_readoutDirection,
            params_eprimeScriptNum = self.params_eprimeScriptNum,
            scanOrder = self.scanOrder,
            scanComplete = self.scanComplete )
        # Handle some additional formatting
        if detailsDict.get('quality') == "usable" or detailsDict.get('quality') == "undetermined":
            detailsDict['quality'] = None
        # Convert the CountScan field to Y/N
        detailsDict['releaseCountScan'] = numberToYN( detailsDict.get('releaseCountScan') )
        # If the scan is counted, Convert the Release field to Y/N
        if detailsDict.get('releaseCountScan') == 'N':
            detailsDict['targetForRelease'] = None
        else:
            detailsDict['targetForRelease'] = numberToYN( detailsDict.get('targetForRelease') )
        # If the scan is targeted for release, Convert the View field to Y/N
        if detailsDict.get('targetForRelease') == 'N':
            detailsDict['viewScan'] = None
        else:
            detailsDict['viewScan'] = numberToYN( detailsDict.get('viewScan') )
        # Append a single-quote to the PE Direction field if it is present because it starts with a +/-
        if detailsDict.get('params_peDirection') is not None:
            detailsDict['params_peDirection'] = "\'" + detailsDict['params_peDirection']
        # Append a single-quote to the Readout Direction field if it is present because it starts with a +/-
        if detailsDict.get('params_readoutDirection') is not None:
            detailsDict['params_readoutDirection'] = "\'" + detailsDict['params_readoutDirection']
        # Extract a dictionary that matches the specified Output Mapping and return it
        return extractDict( detailsDict, csvOrder(outputMap) )

def csvOrder( outputMap ):
    if outputMap == "all":
        order = [
            'sessionDay',
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
            'viewScan',
            'params_shimGroup',
            'params_biasGroup',
            'seFieldMapGroup',
            'params_geFieldMapGroup',
            'dbDesc',
            'params_peDirection',
            'params_readoutDirection',
            'params_eprimeScriptNum',
            'scanOrder',
            'scanComplete' ]
    elif outputMap == "release":
        order = [
            'sessionDay',
            'startTime',
            'dbID',
            'dbType',
            'dbDesc',
            'quality',
            'scanComplete',
            'params_shimGroup',
            'params_biasGroup',
            'seFieldMapGroup',
            'params_geFieldMapGroup',
            'params_peDirection',
            'params_readoutDirection',
            'params_eprimeScriptNum',
            'scanOrder' ]
    elif outputMap == "package":
        order = [
            'subjectName',
            'series_description',
            'dbDesc' ]
    else:
        order = None
    return order

def seriesLabels( outputMap ):
    labelsDict = dict(
        subjectName = "Subject Name",
        sessionLabel = "Session Label",
        sessionDay = "Session Day",
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
        viewScan = "View",
        params_shimGroup = "Shim Group",
        params_biasGroup = "BiasField group",
        seFieldMapGroup = "SE_FieldMap group",
        params_geFieldMapGroup = "GE_FieldMap group",
        dbDesc = "CDB_Description",
        params_peDirection = "PE Direction",
        params_readoutDirection = "Readout Direction",
        params_eprimeScriptNum = "E-Prime Script",
        scanOrder = "Scan Order",
        scanComplete = "Scan Complete" )
    return extractDict( labelsDict, csvOrder(outputMap) )
