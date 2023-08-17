#!/usr/bin/env python

import json
import subprocess
import json
import yaml

__author__ = 'Laraib Kazi | @starlord'
__version__ = 'v.0.9.1'

'''
This script is to assist with VCF upgrades, namely checking the VersionAlias.yml configuration.

Pre-requistes:
- SDDC Manager has to be upgraded to the target VCF BoM.
- The script has to be run as root.

For any questions and concerns, please reach out to me directly at lkazi@vmware.com
'''
CYELLOW = '\033[93m'
CGREEN = '\033[92m'
CRED = '\033[91m'
CEND = '\033[0m'

def loadManifest(sddcVersion):
    # Loads Manifest for Current version of SDDC Manager
    
    lcmFilePath = "/opt/vmware/vcf/lcm/lcm-app/conf/lcmManifest.json"
    with open(lcmFilePath,"r") as f:
        lcmData = json.load(f)
        count = -1
        for entry in lcmData['releases']:
            count = count + 1
            if entry['version'] == sddcVersion:
                index = count
                for bomEntry in entry['bom']:
                    if bomEntry['name'] == "NSX_T_MANAGER":
                        nsxtVersion=bomEntry['version']
                    if bomEntry['name'] == "VCENTER":
                        vcVersion=bomEntry['version']
                    if bomEntry['name'] == "ESX_HOST":
                        esxVersion=bomEntry['version']          
                currentManifestInfo = [nsxtVersion,vcVersion,esxVersion]
                break
        
        f.seek(0)
        count = -1
        for entry in lcmData['releases']:
            count = count + 1
            if count == (index-1):
                for bomEntry in entry['bom']:
                    if bomEntry['name'] == "NSX_T_MANAGER":
                        prev_nsxtVersion=bomEntry['version']
                    if bomEntry['name'] == "VCENTER":
                        prev_vcVersion=bomEntry['version']
                    if bomEntry['name'] == "ESX_HOST":
                        prev_esxVersion=bomEntry['version']
                previousManifestInfo = [prev_nsxtVersion,prev_vcVersion,prev_esxVersion]
                break
    
    return currentManifestInfo, previousManifestInfo

def getAllVersionsFromDB():
    
    # Getting Domain Info
    domain=[]
    p = subprocess.Popen('psql -U postgres -h localhost -d platform -qAtX -c "SELECT id,name,type from domain;"',stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,shell=True)
    output,error = p.communicate()

    for line in output.split("\n"):
        if line != '\n' and line != "":
            domain.append(line.split("|"))
    
    # Getting vCenter Info
    vcenter=[]
    p = subprocess.Popen('psql -U postgres -h localhost -d platform -qAtX -c "SELECT id,vm_hostname,version,status from vcenter;"',stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,shell=True)
    output,error = p.communicate()

    for line in output.split("\n"):
        if line != '\n' and line != "":
            vcenter.append(line.split("|"))
    
    # Getting NSXT Info
    nsxt=[]
    p = subprocess.Popen('psql -U postgres -h localhost -d platform -qAtX -c "SELECT id,cluster_fqdn,version,status from nsxt;"',stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,shell=True)
    output,error = p.communicate()

    for line in output.split("\n"):
        if line != '\n' and line != "":
            nsxt.append(line.split("|"))

    # Getting Host Info
    host=[]
    p = subprocess.Popen('psql -U postgres -h localhost -d platform -qAtX -c "SELECT id,hostname,version,status from host;"',stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,shell=True)
    output,error = p.communicate()

    for line in output.split("\n"):
        if line != '\n' and line != "":
            host.append(line.split("|"))

    # Getting host_and_domain table info
    host_and_domain=[]
    p = subprocess.Popen('psql -U postgres -h localhost -d platform -qAtX -c "SELECT host_id,domain_id from host_and_domain;"',stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,shell=True)
    output,error = p.communicate()

    for line in output.split("\n"):
        if line != '\n' and line != "":
            host_and_domain.append(line.split("|"))

    # Getting vm_and_vm_type_and_domain table info
    vm_and_vm_type_and_domain=[]
    p = subprocess.Popen('psql -U postgres -h localhost -d platform -qAtX -c "SELECT domain_id,vm_id from vm_and_vm_type_and_domain;"',stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,shell=True)
    output,error = p.communicate()

    for line in output.split("\n"):
        if line != '\n' and line != "":
            vm_and_vm_type_and_domain.append(line.split("|"))

    # Current SDDC Manager version:
    p = subprocess.Popen('psql -U postgres -h localhost -d platform -qAtX -c "SELECT version from sddc_manager_controller;"',stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,shell=True)
    output,error = p.communicate()

    sddcVersion=output.split("-")[0]

    return domain,vcenter,nsxt,host,host_and_domain,vm_and_vm_type_and_domain,sddcVersion

def loadVersionAliasYml(component):
    versionAliasFilePath = "/opt/vmware/vcf/lcm/lcm-app/conf/VersionAlias.yml"
    
    try:
        with open(versionAliasFilePath,"r") as f:
            vaYaml = yaml.safe_load(f)
    except:
        return "error"
    
    try:
        return vaYaml['versionAliases'][component]
    except:
        return "None"
    
def bundleAvailabilityLogic(domainId,vcenter,nsxt,host,host_and_domain,vm_and_vm_type_and_domain,sddcVersion):

    # Get current version of NSX-T, VC and ESXi for chosen domain
    for iter1 in vm_and_vm_type_and_domain:
        if iter1[0] == domainId:
            for iter2 in nsxt:
                if iter1[1] == iter2[0]:
                    nsxtVersion = iter2[2]
                    nsxtStatus = iter2[3]
                    break
            for iter3 in vcenter:
                if iter1[1] == iter3[0]:
                    vcVersion = iter3[2]
                    vcStatus = iter3[3]
                    break
    
    for iter1 in host_and_domain:
        if iter1[1] == domainId:
            for iter2 in host:
                if iter1[0] == iter2[0]:
                    esxVersion = iter2[2]
                    break
            for iter3 in host:
                if iter3[0] == iter2[0]:
                    if "ACTIVE" not in iter3[3]:
                        esxStatus = iter3[3]
                        break
                    else:
                        esxStatus = "ACTIVE"
    
    print("\nCurrent Versions Detected:\n")
    print("  SDDC Manager: {}".format(sddcVersion))
    print("  NSX-T: {}".format(nsxtVersion))
    print("  vCenter: {}".format(vcVersion))
    print("  ESXi: {}".format(esxVersion))
    
    print(f"\nUsing VCF {sddcVersion} as the Target VCF BoM.")
    
    print("\nCurrent Status Detected:\n")
    statusChecker("NSX_T_MANAGER", nsxtStatus)
    statusChecker("VCENTER", vcStatus)
    statusChecker("ESX_HOST", esxStatus)
    
    # Get BOM for Current SDDC Version:
    currentManifest, previousManifest = loadManifest(sddcVersion)
    
    # Perform Version Alias Configuration check
    print("\nVersion Alias Detection: ")
    aliasChecker("NSX_T_MANAGER", nsxtVersion, currentManifest[0], previousManifest[0], sddcVersion)
    aliasChecker("VCENTER", vcVersion, currentManifest[1], previousManifest[1], sddcVersion)
    aliasChecker("ESX_HOST", esxVersion, currentManifest[2], previousManifest[2], sddcVersion)
    
    # Check compatibility set validity:
    print("\nCompatibility Sets Detection:")
    print(f"(NOTE: Make changes to compatibility sets only as needed AFTER all of the above checks are GREEN.)\n")
    compatSetError = compatSetChecker(currentManifest, previousManifest)
    if compatSetError == False:
        print(f"\n  [ {CGREEN}\u2713{CEND} ] Required Compatibility Sets found.")

def compatSetChecker(currentManifest, previousManifest):
    # Function to check if we have valid Compatibility Sets for the bundle availability
    
    p = subprocess.Popen('psql -U postgres -h localhost -d lcm -qAtX -c "SELECT compatibility_set_id from compatibility_set;"',stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,shell=True)
    output,error = p.communicate()
    
    foundCompatSets = []
    for line in output.split("\n"):
        if line != '\n' and line != "":
            foundCompatSets.append(line.split(":"))
    
    # vc previous bom + nsxt target bom + esx previous bom
    # vc target bom + nsxt target bom + esx pervious bom
    # vc target bom + nsxt target bom + esx target bom
    requiredSet1 = [previousManifest[1], currentManifest[0], previousManifest[2]]
    requiredSet2 = [currentManifest[1], currentManifest[0], previousManifest[2]]
    requiredSet3 = [currentManifest[1], currentManifest[0], currentManifest[2]]
    requiredCompatSets = [requiredSet1, requiredSet2, requiredSet3]
    
    compatSetError = False
    for element in requiredCompatSets:
        if element not in foundCompatSets:
            print(f"  [ {CRED}\u2717{CEND} ] Required set: {element} is not found in the compatibilitySets.")
            compatSetError = True
    
    return compatSetError

def statusChecker(component, status):
    
    if status == "ACTIVE":
        print(f"  [ {CGREEN}\u2713{CEND} ] {component} is marked {CGREEN}ACTIVE{CEND} for the WLD.")
    else:
        print(f"  [ {CRED}\u2717{CEND} ] {component} is not ACTIVE for the WLD.\n  Please investigate the status of the component and mark as ACTIVE from the database if required.")
    

def aliasChecker(component, dbVersion, currentVersion, baseVersion, sddcVersion):

    AliasCheck = False
    aliasFound = 0
    print(f"\n{component}:")
    if dbVersion == currentVersion:
        # Check if the versions match current SDDC Version BOM
        print(f"\n  [ {CGREEN}\u2713{CEND} ] {component} {dbVersion} is already on VCF {sddcVersion} BoM. No aliasing required.")
    elif dbVersion == baseVersion:
        # Check if the versions match the required previous version, in which case no aliasing is required.
        print(f"\n  [ {CGREEN}\u2713{CEND} ] {component} {dbVersion} is already at the requiredPreviousVersion for upgrading to VCF {sddcVersion} BoM. No aliasing required.")
    else:
        # Get Version Aliasing for component
        vaYaml = loadVersionAliasYml(component)
        if vaYaml == "error":
            print(f"\n  {CRED}Error loading VersionAlias.yml file.{CEND} Please check the file for configuration/syntax errors.")
        elif vaYaml == "None":
            print(f"\n  [ {CRED}\u2717{CEND} ] No entry found for {component} in VersionAlias.yml file.")
            print(f"  Please add an entry for {component} with alias version {dbVersion} and base version {baseVersion} for allowing upgrade to VCF {sddcVersion} BoM.")
        else:
            for entry in vaYaml:
                for aliasEntry in entry['alias']:
                    if aliasEntry == dbVersion:
                        aliasFound += 1
                        if entry['base'] == baseVersion:
                            AliasCheck = True
                        break
            if AliasCheck == True:
                print(f"\n  [ {CGREEN}\u2713{CEND} ] {CGREEN}CORRECT ALIAS FOUND{CEND}: Current Version of {component} {dbVersion} is aliased to base version {baseVersion} for allowing upgrade to VCF {sddcVersion} BoM.")
            elif aliasFound > 0:
                print(f"\n  [ {CRED}\u2717{CEND} ] {CRED}INCORRECT BASE VERSION{CEND}: Current Version of {component} {dbVersion} is aliased to an INCORRECT base version.\n  Please edit the base version to {baseVersion} for allowing upgrade to VCF {sddcVersion} BoM.")
            else:
                print(f"\n  [ {CRED}\u2717{CEND} ] {CRED}NO ALIAS FOUND{CEND} for Current Version of {component} {dbVersion}.\n  Please add an alias for version {dbVersion} with base version as {baseVersion} for allowing upgrade to VCF {sddcVersion} BoM.")
            
            if aliasFound > 1:
                print(f"\n  [ {CYELLOW}!!{CEND} ] Current Version of {component} {dbVersion} is being aliased to multiple base version.\n  Please only alias it to base version {baseVersion} for allowing upgrade to VCF {sddcVersion}BoM.")

        aliasVersionAllowed(dbVersion,baseVersion)

def aliasVersionAllowed(dbVersion,baseVersion):
    # Function to check if the versions are allowed to be aliased in the 
    # application.properties or application-prod.properties files
    
    lcmAppConfLocation = "/opt/vmware/vcf/lcm/lcm-app/conf/"
    p = subprocess.Popen("grep 'allowed.base.versions.for.aliasing' "+lcmAppConfLocation+"application*",stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,shell=True)
    output,error = p.communicate()
    
    def printAliasAllowedInfo(version, filename, exists):
        # This function prints the output of findings if the versions are allowed to be aliased or not
        # depending on the file that info is found in
        if exists == True:
            print(f"\n  [ {CGREEN}\u2713{CEND} ] Version {version} is allowed to be aliased in the {filename} file.")
        else:
            print(f"\n  [ {CRED}\u2717{CEND} ] Version {version} is currently not allowed to be aliased.\n  Please append the version {version} to the entry 'allowed.base.versions.for.aliasing' in the {lcmAppConfLocation}{filename} file.")
    
    for line in output.split("\n"):
        if "application.properties" in line:
            exists = False
            if dbVersion in line:
                exists = True
            printAliasAllowedInfo(dbVersion,"application.properties",exists)
            # exists = False
            # if baseVersion in line:
            #     exists = True
            # printAliasAllowedInfo(baseVersion,"application.properties",exists)
            break
        elif "application-prod.properties" in line:
            exists = False
            if dbVersion in line:
                exists = True
            printAliasAllowedInfo(dbVersion,"application-prod.properties",exists)
            # exists = False
            # if baseVersion in line:
            #     exists = True
            # printAliasAllowedInfo(baseVersion,"application-prod.properties",exists)
            break
        else:
            print(f"\n  [ {CRED}\u2717{CEND} ] {CRED}No entry found for 'allowed.base.versions.for.aliasing'.{CEND}")
            print(f"  Please edit the application-prod.properties file and add the following entry:\n  (Append versions for other components as needed)")
            print(f"\n   allowed.base.versions.for.aliasing={dbVersion},{baseVersion}")

def domainSelector(domain):

    print("\nVCF Domains found:")
    count = -1
    for element in domain:
        count = count + 1
        print(f'[{str(count)}] {element[0]} | {element[1]} | {element[2]}')

    print("")
    print("Select the Domain for which we are testing Version Aliasing:")
    while True:
        try:
            ans_file = input("Select Number: ")
        except:
            ans_file = raw_input("Select Number: ")
        
        # If Selection is beyond the list displayed
        if int(ans_file) > count:
            #logger.error("Invalid selection.")
            continue
        else:
            selection = int(ans_file)
            print(f"\nDomain selected is : {domain[selection][1]} ") 
            break
    
    return domain[selection][0]

def main():

    domain,vcenter,nsxt,host,host_and_domain,vm_and_vm_type_and_domain,sddcVersion=getAllVersionsFromDB()
    domainId = domainSelector(domain)

    bundleAvailabilityLogic(domainId,vcenter,nsxt,host,host_and_domain,vm_and_vm_type_and_domain,sddcVersion)
    print()

if __name__ == "__main__":
    main()
