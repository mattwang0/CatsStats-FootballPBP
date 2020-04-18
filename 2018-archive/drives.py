import requests
from bs4 import BeautifulSoup
from selenium import webdriver
import pandas as pd
import numpy as np

'''
Program to scrape drive data from Davidson football games off their website

ex: https://davidsonwildcats.com/schedule.aspx?path=football

Author: Matt Wang
'''

HEADERS = ['date','opponent','qtr','time','pos','points','n_plays','first_downs_earned','fourth_attempted','fourth_converted']
FILENAME = "drives.csv"

SCHEDULE_LINK = "https://davidsonwildcats.com/schedule.aspx?path=football"

'''
need:
-date x
-opponent x
-qtr x
-time x
* only offense x
-pos start x
-points x
-nplays x
-first_downs_earned x
-fourth_attempted (bool)
-fourth_converted (bool)

TODO:
- test on turnovers and ideally turnovers and defensive scores
- test on kickoff returns for touchdowns
'''


'''
Use Selenium library to circumvent NCAA website's protection against scraping

Returns: a BeautifulSoup object that works on the NCAA site
'''
def get_site(url, n):
    browser = webdriver.Firefox()
    browser.get(url)
    html = browser.execute_script('return document.body.innerHTML')
    browser.close()
    soup = BeautifulSoup(html, 'html.parser')
    if not soup:
        if n < 3:
            return get_site(url, n+1)
        else:
            return None
    return soup


'''
Takes schedule link as argument and returns list of links to boxscores for
games that have been played already
'''
def get_boxscores(link):
    soup = get_site(link, 3)
    base = "https://davidsonwildcats.com/"
    boxscores = []
    
    exts = soup.find_all("li", {"class":"sidearm-schedule-game-links-boxscore"})
    for obj in exts:
        link = base[:-1] + str(obj.a.get('href'))
        if link not in boxscores:
            boxscores.append(link)
    
    return boxscores
    

'''
Scrapes website and returns table with columns corresponding to headers list
'''
def get_drives(link):
    soup = get_site(link, 3)
    
    ##DATE --> date
    date_holder = soup.find('dl', {'class':'text-center inline'})
    date = date_holder.dd.text.encode('ascii', 'ignore')
    
    ##OPPONENT --> opp
    names_holder = soup.find('table', {'class':'sidearm-table'}).tbody.find_all('tr')
    team1 = names_holder[0].find_all('span')[1].text.upper()
    team2 = names_holder[1].find_all('span')[1].text.upper()
    if 'DAVIDSON' in team1:
        opp = team2.encode('ascii', 'ignore')
    elif 'DAVIDSON' in team2:
        opp = team1.encode('ascii', 'ignore')
        
    ##FOR EACH QUARTER
    pbp_holder = soup.find('section', {'id':'play-by-play'}).find('div', \
        {'sidearm-responsive-tabs ui-tabs ui-corner-all ui-widget ui-widget-content sidearm-accessible'})
    periods = pbp_holder.find_all('section')
    
    ##INITIALIZE
    quarter = 0
    table = []
    
    for q in periods:
        drives = q.find_all('table', {'class':'sidearm-table overall-stats highlight-hover collapse-on-small'})
        
        ##FOR EACH DRIVE
        for d in drives:
            ##INITIALIZE
            points = 0
            first_downs_earned = 0
            fourth_attempted = False
            fourth_converted = False            

            header = str(d.find('th').text.upper())
            
            #print "header:", header
            #print ""
            
            ##QUARTER --> QUARTER
            if "START OF" in header:
                quarter = quarter + 1
                
            if "DAVIDSON" not in header:
                continue #we only want offense
            
            ##START TIME OF DRIVE --> time
            loc = header.find('AT ')
            if loc != -1:
                time = header[loc+3 : ].encode('ascii', 'ignore')
            
            ##GET DETAILS    
            rows = d.tbody.find_all('tr')
            for n, r in enumerate(rows[1:]):
                info = r.td.text.upper().encode('ascii', 'ignore') #left column
                
                ##GET START POSITION --> POS
                if n == 0:
                    loc = info.find(' AT ') + 4
                    pos = convert(info[loc:])
                    
                    ##FIND DRIVE SUMMARY FOOTER (DRIVE.TFOOT) --> footer
                    try:
                        footer = d.tfoot.find('td', {'class':'text-bold-on-small'}).text
                    except:
                        continue
                    #print footer
                    
                ##GET NPLAYS BASED ON FOOTER --> N_PLAYS
                n_plays = int(footer[ : footer.find(' plays')])
                if n_plays == 0:
                    continue
                
                ##GET YARDS --> YARDS
                yards = int(footer[ footer.find(' , ') + 3 : footer.find(' yards ') ])
                
                detail = r.find_all('td')[1].text.upper().replace('\n', '').replace('  ', '').encode('ascii', 'ignore') #right column
                
                ##HANDLE POINTS --> POINTS
                if "TOUCHDOWN" in detail and "NO PLAY" not in detail:
                    points = 6
                if "FIELD GOAL ATTEMPT" in detail:
                    if " GOOD " in detail:
                        points = 3
                
                ##HANDLE FIRST DOWNS --> FIRST_DOWNS_EARNED
                if "1ST DOWN " in detail and "TOUCHDOWN" not in detail:
                    first_downs_earned = first_downs_earned + 1
                
                ##HANDLE 4TH DOWNS ATTEMPTED
                keywords = ['punt','timeout','field goal']
                if "4TH" in info:
                    went_for_it = True
                    for word in keywords:
                        if word.upper() in detail:
                            went_for_it = False
                    if went_for_it:
                        fourth_attempted = True
                
                ##HANDLE 4TH DOWNS CONVERTED
                if fourth_attempted:
                    if "1ST DOWN" in detail or "TOUCHDOWN" in detail:
                        fourth_converted = True
                    
            #print 
            #print "nplays:", n_plays
            #print "yards:", yards
            #print "first downs:", first_downs_earned
            #print "points:", points
            #print "attempted:", fourth_attempted
            #print "conveted:", fourth_converted
            
            table.append([date,opp,quarter,time,pos,points,n_plays,first_downs_earned,fourth_attempted,fourth_converted])
    
    df = pd.DataFrame(data=table, columns=HEADERS)
    ##remove rows if n_plays is 0
    df = df[df.n_plays != 0]
    
    with open(FILENAME, 'a') as f:
        df.to_csv(f,header=False,index=False)
    
    print opp, date


'''
Takes position on field as string and returns position as integer using 
negative numbers to mark your side of the field and positive numbers to mark
your opponent's

ex: WLU28 --> -28
'''
def convert(pos):
    digits = '0123456789'
    new = ''
    if 'DAV' in pos:
        ##remove all non numbers + make negative
        for i in range(len(pos)):
            if pos[i] in digits:
                new = new + pos[i]
        return int(new) * -1
    else:
        ##just remove all non numbers and return int form
        for i in range(len(pos)):
            if pos[i] in digits:
                new = new + pos[i]
        return int(new)
    

'''
'''
def main():
    boxscores = get_boxscores(SCHEDULE_LINK)
    for link in boxscores:
        get_drives(link)
    
    
    
    
if __name__ == "__main__":
    main()
        
    print "**done**"