
#Final version...

#LinkChecker 1.0

#Tkinter tester
# Integrated PDF and Webpage


import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import tkinter.scrolledtext as scrolledtext

import pikepdf
import asyncio
import aiohttp
from aiohttp import ClientTimeout
import requests
import urllib.request
from bs4 import BeautifulSoup
import re
import time
import os
import threading



# button to browse file
def browseFile():
    filePath = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
    if filePath:
        fileInput.delete(0, tk.END)
        fileInput.insert(0, filePath)


#update radio button output value
def radio():
    value = radioSelect.get()
    #print(value)
    resultText.insert(tk.END, f"radio value: {value}\n")
    #new = tk.Label(root,text=value)
    #new.pack()


#decide which program to run, PDF or WEB
#def programFilter():
    
    
#global lists for WebPage linkchecker
masterGood = []
masterBad = []
urlFailed = []
masterFilter = []

#TK controls
running = 0
    


# create gui tkinter window
root = tk.Tk()

root.geometry("600x600")
root.title("Link Checker")
style = ttk.Style()
style.theme_use('alt')
#'classic', 'alt'





# PDF - linkchecker
#----------------------------------------------------
# async check link run
def checkLinks():
    asyncio.run(runCheckLinks())

# main function
async def runCheckLinks():
    filePath = fileInput.get()
    if filePath:
        pdfFile = pikepdf.Pdf.open(filePath)
        totalUrls = {}
        brokenUrls = {}
        # simulate real user
        userAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        # get urls from pdf
        def getUrls():
            for pageNumber, page in enumerate(pdfFile.pages, start=1):
                annots = page.get("/Annots")
                if annots:
                    for annot in annots:
                        annotation = annot.get("/A")
                        if annotation and isinstance(annotation, pikepdf.Dictionary):
                            uri = annotation.get("/URI")
                            if uri:
                                url = str(uri)
                                # exclude internal links
                                if url not in totalUrls and not url.startswith("https://ecampusontario.pressbooks.pub/"):
                                    totalUrls[url] = [pageNumber]
                                # only append page numbers of one same url
                                elif url in totalUrls:
                                    totalUrls[url].append(pageNumber)

        # check urls
        async def checkUrlsAsync(session, url, pageNumber):
            try:
                async with session.get(url, headers={'User-Agent': userAgent},timeout=20) as response:
                    if response.status != 200:
                        if url not in brokenUrls:
                            brokenUrls[url] = {"pages": [pageNumber], "reasons": [f"{response.status} {response.reason}"]}
                        else:
                            if pageNumber not in brokenUrls[url]["pages"]:
                                brokenUrls[url]["pages"].append(pageNumber)
            except aiohttp.ClientError as e:
                if url not in brokenUrls:
                    brokenUrls[url] = {"pages": [pageNumber], "reasons": [str(e)]}
                else:
                    if pageNumber not in brokenUrls[url]["pages"]:
                        brokenUrls[url]["pages"].append(pageNumber)
            except asyncio.TimeoutError as e:
                pass
            except UnicodeError as e:
                pass
            except:
                pass

        # check urls async
        async def checkUrls():
            async with aiohttp.ClientSession(timeout=ClientTimeout(total=120)) as session:
                tasks = []
                for url, pageNumbers in totalUrls.items():
                    for pageNumber in pageNumbers:
                        tasks.append(checkUrlsAsync(session, url, pageNumber))
                await asyncio.gather(*tasks)

        # result print
        def printResult():
            resultText.insert(tk.END, f"Printing results...\n")
            
            # empty result
            resultText.delete(1.0, tk.END)

            # write output in textarea & txt file
            # get file path
            directory = os.path.dirname(os.path.abspath(filePath))
            # get pdf name
            fileName = os.path.basename(filePath)
            outputPath = os.path.join(directory, f"{fileName}-PDF.txt")
            outputTxt = open(outputPath, "w")

            for url, data in brokenUrls.items():
                pagesStr = ', '.join(map(str, data["pages"]))
                reasonsStr = '\n'.join(data["reasons"])
                resultText.insert(tk.END, f"Link: {url}\nPages: {pagesStr}\nReasons: {reasonsStr}\n\n")
                # write in txt file
                outputTxt.write(f"Link: {url}\nPages: {pagesStr}\nReasons: {reasonsStr}\n\n")


            resultText.insert(tk.END, f"Total broken links: {len(brokenUrls)}\n")
            resultText.insert(tk.END, f"Total links: {len(totalUrls)}\n")

            

        # main
        getUrls()
        await checkUrls()
        printResult()
        #stop progBar
        progBar.stop()
        global running
        running = 0
#------------------------------------------------------





# WebPage Linkchecker
#------------------------------------------------------
#grab website main page, as internal data.
def getHtml(webSite):

    header = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept-Language': 'en-GB,en;q=0.5',
            'Referer': 'https://www.google.ca',
            'DNT': '1'
            }

    #try to grab page content, 403 may happen so catch it if so...
    try:
        urlRequest = urllib.request.Request(webSite,headers=header)
        #open url
        webUrl = urllib.request.urlopen(urlRequest)
    except Exception as e:
        print(e)
        return None
    #open web
    #webUrl = urllib.request.urlopen(webSite)

    #get page info in bytes
    data = webUrl.read()

    #print(webUrl.getcode())

    #parse HTML
    soup = BeautifulSoup(data,'html.parser')

    return soup


# Secondary Directory --- Non-dependent on CSS class standards...
#
def getInternalContent(soup,webUrl):
    #INTERNAL links for the content of the whole book
    contentLinks = []

    #grab string of 'https:// --- end of second directory'
    secondDirectory = getSecondaryDirectory(webUrl)

    #list of all anchor tags in the page...
    anchorList = soup.find_all('a')

    contentLinks.append(webUrl) #add home page to internalList
    for link in anchorList:

        #check if links are NOT https:// type, or anchor has no href 
            #Since JS and CSS hrefs are common...
        #Both cases here
        try:
            #if contains 'https://' then do nothing and move to directory check
            if('https://' not in link['href']):
                continue
        except:
            #anchor has no href. tag['href'] throws error...
            #print('Anchor has no link.. Ignore this.')
            continue

        #make sure sign in, home, and download links are not counted as content
            #Since they link to second directory
        if(link['href'] == webUrl):
            continue
        if('wp-login.php' in link['href']):
            continue
        #elif('#main' in link['href']):
        #    continue
        elif('open/download?type' in link['href']):
            continue

        #check if 2nddirectory is in the found link
            #if True, then check if the whole link is not in the contentList
            #if True, then add the link to the content list
        if secondDirectory in link['href']:
            if link['href'] not in contentLinks:
                contentLinks.append(link['href'])
                
    #print('Length of content List 2ND Directory: ',end='')
    #print(len(contentLinks))

    #return list of all the books content links
    return contentLinks



#get second domain name for getInternalContent()
#
def getSecondaryDirectory(webUrl):
    countSlashes = 0
    secondaryDomain = ''
    for i in range(len(webUrl)):
        #count slashes
        if(webUrl[i] == '/'):
            countSlashes += 1
            if(countSlashes == 4):
                #grab the slash as well...
                secondaryDomain = webUrl[0:i+1]
    return secondaryDomain


#Called from within checkExternalLinks()
#for CLASS STANDARD SEARCH
def getDomainName(webSite):
    #Find main domain name
    #Use to find EXTERNAL LINKS... Also use to ignore INTERNAL LINKS.
    countSlashes = 0
    #regexpattern for given domain name
    domainRegex = ''

    for i in range(len(webSite)):
        #count slashes, find index of THIRD slash.. Thats domain name...
        if(webSite[i] == '/'):
            countSlashes += 1
            if(countSlashes == 3):
                domainRegex = webSite[0:i+1]
                #could go [8:i] to exclude https://
                break
    return domainRegex
    #print('Domain name: ',domainRegex)


#get page to add to dictheader for EXTERNAL link
def getPage(link):
    countSlashes = 0
    length = len(link)
    page = ''

    for i in range(length):
        if(link[i] == '/'):
            countSlashes += 1
            if(countSlashes == 4):
                page = link[i:]
    return page



#return CLEAN list of ALL external links within the internalLink given...
    #RETURNS - list of dict per link
def filterRoughAnchors(internalLink,webSite):
    cleanList = []
    
    #internalLinks
        #get parsed soup from URL

    soup = getHtml(internalLink)
    #soup may throw error, if none return empty list. Link didn't respond.
    if(soup == None):
        return cleanList

        #list of all anchor tags in the page...
    anchorList = soup.find_all('a')

        #get domain name to filter out external links
    domainRegex = getDomainName(webSite)
        #regexObject to compare to
    regexObject = re.compile(domainRegex)

    count = 0
    for i in range(len(anchorList)):

        linkDict = {}
            #HTML anchor tag as element in list
        tag = anchorList[i]

            #check if links are NOT https:// type, or anchor has no href 
                #Since JS and CSS hrefs are common...
            #Both cases here
        try:
            if('https://' not in tag['href']):
                continue
        except:
                #anchor has no href. tag['href'] throws error...
            #print('Anchor has no link.. Ignore this.')
            continue

            #search link
        searchObject = regexObject.search(tag['href'])
            
            #Link from anchor tag as STRING
        
            #Look for searchObject = None, means link is EXTERNAL
        if(searchObject == None):
                #add link to cleanList.
            #if(tag['href'] in masterGood):
             #    print('Already checked...')
              #   continue
            
            #if(tag['href'] in cleanList):
             #   print('Already in cleanlist...')
              #  continue
            
                #print(tag['href'])
                #get page title... Chapter section easy to look up
            titleOfPage = soup.title.string
            keyWord = tag.string
            linkDict.update({'Status':0})
            linkDict.update({'Url':tag['href']})
            linkDict.update({'Page':internalLink})
            linkDict.update({'Page Title':titleOfPage})
            linkDict.update({'Keyword':keyWord})
                #maybe grab page title too...
            cleanList.append(linkDict)      
        else:
            continue
        
    #return list of dicts for each link
    return cleanList


#receives a link to check the status of.
async def linkChecker1(session,linkDict):

    #reportDict = {}

    url = linkDict['Url']
    try:
        async with session.get(url) as response:
            if response.status == 200:
                masterGood.append(url)

            elif response.status == 401:
                linkDict['Status'] = '401-Unauthorized'
                masterBad.append(linkDict)
            elif response.status == 403:
                linkDict['Status'] = '403-Forbidden'
                masterBad.append(linkDict)
                
            elif response.status == 404:
                linkDict['Status'] = '404-Not Found'
                masterBad.append(linkDict)

            elif response.status == 410:
                linkDict['Status'] = '410-Broken'
                masterBad.append(linkDict)
            else:
                linkDict['Status'] = 'Unknown Status'
                masterBad.append(linkDict)
                
            #return await response.text()
            return await response.read()
        
    except asyncio.TimeoutError:
        #linkDict['Status'] = 'Timed Out'
        #masterBad.append(linkDict)
        pass
    
    except aiohttp.ClientConnectorError as e:
        linkDict['Status'] = 'Cannot connect to host doi'
        masterBad.append(linkDict)
        
    except Exception as e:
        #linkDict['Status'] = 'Unknown Error'
        linkDict['Status'] = e

        masterBad.append(linkDict)



#collect list of dictionaries of broken links + info
async def main(externalLinks,webSite):

    userAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    
    header = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept-Language': 'en-GB,en;q=0.5',
        'Referer': 'https://www.google.ca',
        'DNT': '1'
        }

    #async 
    async with aiohttp.ClientSession(timeout=ClientTimeout(total=180),headers=header) as session:
        taskList = []
        
        for extDict in externalLinks:
            #catch2 = True
            #dict from list at i

            #this now takes a dict again
            taskList.append(asyncio.create_task(linkChecker1(session,extDict)))
 
        #print('Tasks started...')
        await asyncio.gather(*taskList)
        #print(result[0]['Status'])
#event loop end

#grabs all external links from every INTERNAL page
def grabExternal(internalLinks,webSite):

    externalList = []

    #gather all external links for each internal page into one list^^
    for internalLink in internalLinks:

        cleanList = filterRoughAnchors(internalLink,webSite)
        externalList.extend(cleanList)

    return externalList


#filter broken list of dictionaries
def filterBroken(badLinks):
    
    #list for urls checked
    filteredUrls = []
    #list of new filter/grouped dictionaries for each bad link
    filteredList = []
    
    for i in range(len(badLinks)-1):
        url = badLinks[i]['Url']

        if(url in filteredUrls):
            continue

        #hold current dictionary for link being checked.
        curDict = badLinks[i]

        newDict = {}
        #add url being checked to new dict
        newDict.update({'Status':curDict['Status']})
        newDict.update({'Url':url})
        #list so we can add multiple of Page Title and Keyword
        newDict.update({'Page Title':[curDict['Page Title']]})
        newDict.update({'Keyword':[curDict['Keyword']]})

        for j in range(i+1,len(badLinks)):
            url2 = badLinks[j]['Url']
            if(url2 == url):

                #grab Page title and keyword and add to new dicts list..
                pageTitle = badLinks[j]['Page Title']
                keyWord = badLinks[j]['Keyword']

                #add new entry into dictionary lists
                newDict['Page Title'].append(pageTitle)
                newDict['Keyword'].append(keyWord)

        #add already checked url to list
        filteredUrls.append(url)
        #add new dict to list
        filteredList.append(newDict)

    return filteredList


#print out to tkiner GUI
#print all 403s first in their own section, and then the rest of the broken links
def printToGui(filteredList):

    #find 403s, then print them all out
    resultText.insert(tk.END, f'\n\n403 links found\n')
    resultText.insert(tk.END, f'-------------------------\n\n')
    
    #find 403s and print them out
    for dictItem in filteredList:
        if(dictItem['Status'] == '403-Forbidden'):
            resultText.insert(tk.END, f"\nStatus: {dictItem['Status']}\n\n")
            resultText.insert(tk.END, f"Url: {dictItem['Url']}\n")

            #403 link has more than one...
            if(len(dictItem['Page Title']) > 1):
            
                resultText.insert(tk.END, f"\nFound in:\n\n")
                
                #times length by two so we can grab from both Page Title + Keyword
                for i in range(len(dictItem['Page Title'])):
                    resultText.insert(tk.END, f"Page Title: {dictItem['Page Title'][i]}\n")
                    resultText.insert(tk.END, f"Keyword: {dictItem['Keyword'][i]}\n")

            else:
                resultText.insert(tk.END, f"Page Title: {dictItem['Page Title'][0]}\n")
                resultText.insert(tk.END, f"Keyword: {dictItem['Keyword'][0]}\n")

            resultText.insert(tk.END, f'\n------\n')

    #line to separate 403s from other links 
    resultText.insert(tk.END, f'\n-------------------------\n\n')
    resultText.insert(tk.END, f'Broken Links\n\n-------------------------\n\n')

    #loop through and print NON 403 links

    for dictItem in filteredList:
        if(dictItem['Status'] != '403-Forbidden'):
            resultText.insert(tk.END, f"\nStatus: {dictItem['Status']}\n\n")
            resultText.insert(tk.END, f"Url: {dictItem['Url']}\n\n")


            #403 link has more than one...
            if(len(dictItem['Page Title']) > 1):
            
                resultText.insert(tk.END, f"\nFound in:\n\n")
                
                #times length by two so we can grab from both Page Title + Keyword
                for i in range(len(dictItem['Page Title'])):
                    resultText.insert(tk.END, f"Page Title: {dictItem['Page Title'][i]}\n")
                    resultText.insert(tk.END, f"Keyword: {dictItem['Keyword'][i]}\n\n")

            else:
                resultText.insert(tk.END, f"Page Title: {dictItem['Page Title'][0]}\n")
                resultText.insert(tk.END, f"Keyword: {dictItem['Keyword'][0]}\n")
        
            resultText.insert(tk.END, f'\n------\n')

    resultText.insert(tk.END, f"\nAmount of broken links: {len(filteredList)}")


#grab only second directory word ...
def getSecondDirOnly(webSite):
    slash=0
    name = ''
    #start last to below...
    for i in range(len(webSite)-2,0,-1):
        if(webSite[-1] == '/'):
            slash=-1
        if(webSite[i] == '/'):

            if(slash == 0):
                name = webSite[i+1:len(webSite)-2]
                break
            else:
                name = webSite[i+1:len(webSite)-1]
                break
    return name
        
        
        

#print output to .txt file in directory...
def printToFile(filteredList,webSite):

    #grab directory, normalize, and add filename to it
    dirr = os.getcwd()
    new = dirr.replace('\\',"\\\\")
    secondDirectory = getSecondDirOnly(webSite)
    fileName = new+'\\\\'+secondDirectory+'-Webpage'+'.txt'
    #open text file to write info to.
    file = open(fileName,'w')
    #grab 
    file.write('\nLink Checker Report\n---\n')
    file.write(f'Website Link: {webSite}\n')
    file.write(f'\nBook Name: {secondDirectory}\n\n')
    file.write('-----------------------\n\n')
    file.write('Broken Links\n')
    file.write('---\n')
    file.write(f'Number of broken links: {len(filteredList)}\n\n\n')
    file.write('403 Section:\n------\n\n')

    #find 403s and print them out
    for dictItem in filteredList:
        if(dictItem['Status'] == '403-Forbidden'):
            #write same to text file..
            file.write(f"\nStatus: {dictItem['Status']}\n\n")
            file.write(f"Url: {dictItem['Url']}\n\n")

            #403 link has more than one...
            if(len(dictItem['Page Title']) > 1):
                file.write(f"Found in:\n\n")
                
                #times length by two so we can grab from both Page Title + Keyword
                for i in range(len(dictItem['Page Title'])):
                    file.write(f"Page Title: {dictItem['Page Title'][i]}\n")
                    file.write(f"Keyword: {dictItem['Keyword'][i]}\n")
            else:
                file.write(f"Page Title: {dictItem['Page Title'][0]}\n")
                file.write(f"Keyword: {dictItem['Keyword'][0]}\n")
            file.write('\n-------\n')

    #line to separate 403s from other links 
    file.write('\n-------------------------')

    #loop through and print NON 403 links
    for dictItem in filteredList:
        if(dictItem['Status'] != '403-Forbidden'):
            file.write(f"\n\nStatus: {dictItem['Status']}\n\n")
            file.write(f"Url: {dictItem['Url']}\n")
            
            #403 link has more than one...
            if(len(dictItem['Page Title']) > 1):
                file.write('\nFound in:\n')
                
                #times length by two so we can grab from both Page Title + Keyword
                for i in range(len(dictItem['Page Title'])):
                    file.write(f"Page Title: {dictItem['Page Title'][i]}\n")
                    file.write(f"Keyword: {dictItem['Keyword'][i]}\n\n")
            else:
                file.write(f"Page Title: {dictItem['Page Title'][0]}\n")
                file.write(f"Keyword: {dictItem['Keyword'][0]}\n")
            file.write('\n------\n')
    #close file.
    file.close()

    
#main function - Run TWO Co-Routines from here...
def mainStart():

    global running
    #grab webpage given from GUI
    webSite = fileInput.get()
    
    #---Part 01---
    #Parsed masterLink HTML content in soup
    soup = getHtml(webSite)

    #Catch error in getHtml
        #returns None if error, so nothing is ran
    if(soup != None):

        #clear previous bad list if used..
        masterBad.clear()

        #---STEP 01---
        #get all content links of book, + main page..
        internalLinks = getInternalContent(soup,webSite)  #BY SECOND DIRECTORY

        #master list of all external
        checkStatus = grabExternal(internalLinks,webSite)    


        #use this to run main which would be 
        if __name__ == "__main__":
            #async run tasks on whole list of every external link
            asyncio.run(main(checkStatus,webSite))


        #filter broken links into single dictionaries per link
        cleanList = filterBroken(masterBad)

        #print resuults to GUI
        printToGui(cleanList)
        #print to file
        printToFile(cleanList,webSite)

        
    else:
        progBar.stop()
        resultText.insert(tk.END, f"\nThere was an error with grabbing the links resources. Try again or restart.\n")

    
    #stop progBar
    progBar.stop()
    running = 0




#-------------------------------------------------------------------
#
#
#main to control which program gets called to run.
def linkMain():

    #empty textarea everytime program runs
    resultText.delete(1.0, tk.END)
    
    #allow global assignment to running
    global running
    #grab radio value to see which file we are running on
    value = radioSelect.get()
    #grab filepath to make sure its not empty
    filePath = fileInput.get()

    if(filePath == ''):
        resultText.insert(tk.END, f"Field empty.Please enter a PDF or hyperlink above...\n")

    elif(running == 0):
        global progBar
        #scan pdf for bad links
        if(value == 'pdf'):
            
            webSite = fileInput.get()

            #
            if(not os.path.exists(webSite) or webSite[-3:] != 'pdf'):
                resultText.insert(tk.END, f"Please give a PDF file, or select webpage for hyperlinks.\n")

            else:
                progBar = ttk.Progressbar(frame,orient=tk.HORIZONTAL, length=200,mode='indeterminate')
                progBar.grid(row=3, column=1, columnspan=2,pady=20)
                progBar.start()
                running = 1
                threading.Thread(target=checkLinks).start()
        #scan webpage for bad links
        else:
            webSite = fileInput.get()

            if(webSite[0:4] == 'http'):

                progBar = ttk.Progressbar(frame,orient=tk.HORIZONTAL, length=200,mode='indeterminate')
                progBar.grid(row=3, column=1, columnspan=2,pady=20)
                running = 1
                resultText.insert(tk.END, f"checking: {webSite}\n")
                #start progress bar
                progBar.start()
                #start thread for linkcheck
                threading.Thread(target=mainStart).start()
            else:
                #print into console that a hyperlink was not given for webpage link check
                resultText.insert(tk.END, f"Please give a hyperlink for webpage option.\n")
    

# Code for GUI
#------------------------------------
#new code for Tk
frame = ttk.Frame(root)
frame.grid(column=0,row=0)

#create grid
frame.columnconfigure(0,weight=1)
frame.columnconfigure(1,weight=1)
frame.columnconfigure(2,weight=1)
frame.columnconfigure(3,weight=1)

frame.rowconfigure(0,weight=1)
frame.rowconfigure(1,weight=1)
frame.rowconfigure(2,weight=1)
frame.rowconfigure(3,weight=1)

#create label
label = tk.Label(frame, text="Select File:", font=('Arial',10))
label.grid(row=0,column=0,pady=10,sticky="WE")

#create input for pdf or link
fileInput = tk.Entry(frame)
fileInput.grid(row=0, column=1, pady=10,columnspan = 2, sticky = tk.W+tk.E)

#get fiile browse button
browseButton = tk.Button(frame, text="Browse", font=('Arial',10),command=browseFile)
browseButton.grid(row=0, column=3, padx=10, pady=10)

#keep track of radio variable
radioSelect = tk.StringVar(root, 'pdf')

#configure function call with program...
radioButton01 = ttk.Radiobutton(frame, text='Digital PDF', variable=radioSelect, value='pdf')
radioButton01.grid(row=2, column=1, pady=10)
radioButton02 = ttk.Radiobutton(frame,text='Webpage', variable=radioSelect, value='web')
radioButton02.grid(row=2, column=2, pady=10)

#final confirm button...
check = tk.Button(frame,text='Confirm', font=('Arial',10),command=linkMain)
check.grid(row=2,column=3, pady=10)

#style frame
frame['borderwidth'] = 5
frame['relief'] = 'sunken'
frame.pack(fill='x')

#create textbox with scroll bar to send results too.
resultText = scrolledtext.ScrolledText(root, undo=True)
resultText.pack(pady=5,padx=10,expand=True,fill='both')

devLabel = tk.Label(root, text='Developed by: Jayne You and Carter McCauley', font=('Arial',8))
devLabel.pack(pady=15)


#run tkinter
root.mainloop()