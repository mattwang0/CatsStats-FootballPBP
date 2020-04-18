import requests
from bs4 import BeautifulSoup
from selenium import webdriver
import pandas as pd
import numpy as np

'''
Program to scrape drive data from Washington and Lee football games off
their website

ex: http://www.generalssports.com/sports/fball/2017-18/boxscores/20171014_v00h.xml?view=plays

Author: Matt Wang
'''

HEADERS = ['opponent','qtr','time','offdef','pos','points','nplays','first_downs_earned','fourth_attempted','fourth_converted']

'''
Scrapes website and returns list of all plays in game, as well as opponent 
'''
def get_plays(link):
    soup = get_site(link)
    
    ##GET AND FORMAT EACH PLAY --> list: PLAYS
    table_soup = soup.find_all('div', {'class':'stats-fullbox clearfix'})[1].find('tbody')
    plays_soup = table_soup.find_all('tr')[1:]
    plays = []
    #print len(plays_soup)
    for p in plays_soup:
        plays.append(p.text.strip().rstrip().replace('\n', ' ').\
                     replace('        ', ' ').encode('ascii','ignore').upper())
    
    #for p in plays: print p
    
    ##GET NAME OF OPPONENT
    header = soup.find('div', {'class':'stats-wrapper clearfix'}).find('tr').text.strip().rstrip().upper()
    loc1 = header.find(' VS. ')
    loc2 = header.find(' AT ')
    team1 = header[:loc1]
    team2 = header[loc1+5 : loc2]
    
    if 'WASHINGTON AND' in team1 or 'WASHINGTON &' in team1:
        opponent = team2
    else:
        opponent = team1
        
    return plays, opponent.encode('ascii','ignore')
    

'''
Use Selenium library to circumvent NCAA website's protection against scraping

Returns: a BeautifulSoup object that works on the NCAA site
'''
def get_site(url):
    browser = webdriver.Firefox()
    browser.get(url)
    html = browser.execute_script('return document.body.innerHTML')
    browser.close()
    return BeautifulSoup(html, 'html.parser')


'''
Take a list of plays (and opponent name) and produces a nested list where each
row corresponds to information for one drive.  Also calculates number of plays,
points, first downs earned, fouth downs earned and attempted
'''
def get_drives(plays, opponent):
    ##break up plays into drives. start by finding locations of drive start markers
    start_locs = [] #indicies of drive start locations
    for n, p in enumerate(plays):
        if " DRIVE START " in p:
            start_locs.append(n)
    start_locs.append(len(plays)-1)
    
    drives = []
    qtr = 1
    for n, x in enumerate(start_locs):
        if n == len(start_locs)-1:
            continue
        
        drive = plays[x:start_locs[n+1]]
        
        ##RUN THROUGH EACH DRIVE
        points = 0
        first_downs_earned = -1
        fourth_converted = False
        fourth_attempted = False
        quarter_middrive = False #if quarter is incremented during drive
                                 #used with qtr_toadd to get quarter at start of drive, not end
        for nn, play in enumerate(drive):
            ##track quarter
            if "2ND" in play and "AND" not in play:
                qtr = 2
                quarter_middrive = True
            elif "3RD" in play and "AND" not in play:
                qtr = 3
                quarter_middrive = True
            elif "4TH" in play and "AND" not in play:
                qtr = 4
                quarter_middrive = True
            
            if " DRIVE START " in play:
                ##handle offense/defense
                if "WASHINGTON AND LEE " in play or 'WASHINGTON & ' in play: #111
                    offdef = "OFFENSE"
                else:
                    offdef = "DEFENSE"
                
                ##get starting field location
                start = play.find(' AT ') + 4
                end = play.find(' ', start)
                pos = convert(play[start:end])
                
                ##get starting time
                start = play.find('DRIVE START AT ') + 15
                end = play.find('.', start) 
                time = play[start:end]
            
            ##handle points from drive
            ##TEST
            if "FIELD GOAL ATT" in play and "HOPKINS" in opponent:
                pass
            
            if " TOUCHDOWN" in play and "NO PLAY" not in play: 
                points = 6  
            elif "FIELD GOAL ATT" in play and " GOOD," in play and "NO PLAY" not in play:
                points = 3
            
            ##track 1st and 10s/goals to know whether or not 2 first downs were earned on drive
            if "1ST AND " in play and (" RUSH " in play or " PASS " in play or " SACK" in play) and 'PENALTY' not in play:
                first_downs_earned = first_downs_earned + 1
            
            ##track 4th down converted and 4th down attempted
            if "4TH" in play and " AND " in play:
                if " RUSH " in play or " PASS " in play or " SACKED" in play:
                    if "TIMEOUT" not in play:
                        fourth_attempted = True
                        
                        if "TOUCHDOWN" in play or "1ST AND " in drive[nn+1]:
                            fourth_converted = True
                
            
            ##get number of plays in drive
            if " ELAPSED" in play:
                end = play.find(' PLAYS')
                nplays = int(play[:end])
        
        qtr_toadd = qtr
        if quarter_middrive:
            qtr_toadd = qtr_toadd - 1
        drives.append([opponent,qtr_toadd,time,offdef,pos,points,nplays,first_downs_earned,fourth_attempted,fourth_converted])

    for d in drives:
        print d
    
    return drives


'''
Takes position on field as string and returns position as integer using 
negative numbers to mark your side of the field and positive numbers to mark
your opponent's

ex: WLU28 --> -28
'''
def convert(pos):
    digits = '0123456789'
    new = ''
    if 'WLU' in pos:
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
Driver
'''
def run(links):
    all_data = []
    
    for link in links:
        plays, opponent = get_plays(link)
        temp_data = get_drives(plays, opponent)
        all_data = all_data + temp_data
        
        for line in temp_data:
            print line
        
    df = pd.DataFrame(data=all_data,columns=HEADERS)
    df.to_csv('wlu-offense.csv',index=False)


'''
'''
def main():
    print HEADERS
    run(['http://www.generalssports.com/sports/fball/2017-18/boxscores/20171014_v00h.xml?view=plays',
         'http://www.generalssports.com/sports/fball/2017-18/boxscores/20171028_lmc2.xml?view=plays',
         'http://www.generalssports.com/sports/fball/2017-18/boxscores/20170930_htuq.xml?view=plays',
         'http://www.generalssports.com/sports/fball/2017-18/boxscores/20170901_dp1x.xml?view=plays',
         'http://www.generalssports.com/sports/fball/2017-18/boxscores/20171021_nqqu.xml?view=plays'])


if __name__ == "__main__":
    main()
        
    print "**done**"


'''
CORRECTIONS
- JHU 1st 4:55 should have no 1st downs
'''