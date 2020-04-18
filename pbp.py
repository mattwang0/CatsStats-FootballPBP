import requests
from bs4 import BeautifulSoup
from selenium import webdriver
import pandas as pd
import numpy as np

'''
Program to scrape play by play data from Davidson football games off the
Davidson football website

TO RUN:
- make sure "YEAR" global variable is correct
- paste game url when prompted (ex: https://davidsonwildcats.com/boxscore.aspx?id=5041&path=football)

Author: Matt Wang
'''

YEAR = "2019"

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
Returns date, opponent, quarter, time, down, yards_gained, field_pos, pass/run,
player1 (receiver/runner), player2 (qb) for each play in a single game

Args:
soup

Returns:
df with all data, ready to be sent to csv
'''
def get_pbp(soup, team):
    table = []
    
    date_holder = soup.find('dl', {'class':'text-center inline'})
    date = date_holder.dd.text.encode('ascii', 'ignore') #get date
    
    #find opponent name
    names_holder = soup.find('table', {'class':'sidearm-table'}).tbody.find_all('tr')
    team1 = names_holder[0].find_all('span')[1].text.upper()
    team2 = names_holder[1].find_all('span')[1].text.upper()
    if team in team1:
        opp = team2.encode('ascii', 'ignore')
    elif team in team2:
        opp = team1.encode('ascii', 'ignore')
    
    # pbp_holder = soup.find('section', {'id':'play-by-play'}).find('div', \
    #     {'sidearm-responsive-tabs ui-tabs ui-corner-all ui-widget ui-widget-content'})
    # periods = pbp_holder.find_all('section')

    pbp_holder = soup.find('section', {'id':'play-by-play'})
    periods = pbp_holder.find_all('section')
    
    print date, opp
    
    offdef = "OFFENSE" #"OFFENSE" or "DEFENSE"
    first_play_of_game = True #because first drive doesn't mark 'start drive' which messes up p_n_ten tracker
    quarter = 0 #initialize
    time = "15:00" #initilaize
    #for data in each period..
    for q in periods:
        drives = q.find_all('table', {'class':'sidearm-table overall-stats highlight-hover collapse-on-small'})
        
        
        #for each drive..
        for d in drives:
            
            header = d.find('th').text.upper()
            
            if team in header:
                offdef = "OFFENSE"
            elif "START OF" not in header:
                offdef = "DEFENSE"
                
            if "START OF" in header:
                quarter = quarter + 1
            
            loc = header.find('AT ')
            if loc != -1:
                time = header[loc+3 : ].encode('ascii', 'ignore')
            
            p_n_ten = "NO" #'P AND 10' marks first play of each series
            
            #actually get details
            rows = d.tbody.find_all('tr')
            for r in rows[1:]: #avoid first entry
                #if the row has kickoff data, ignore
                test = len(r.find_all('td'))
                if test < 2:
                    continue
                
                if first_play_of_game:
                    p_n_ten = 'YES'
                    first_play_of_game = False
                
                #continue if kickoff, timeout, punt in detail
                #right-er column
                detail = r.find_all('td')[1].text.upper().replace('\n', '').encode('ascii', 'ignore')
                buzzwords = [' punt ',' kickoff ','timeout ','kick attempt','start of']
                skip_flag = False
                for word in buzzwords:
                    if word.upper() in detail:
                        skip_flag = True
                if skip_flag:
                    continue
                
                temp = [YEAR, offdef, date, opp, quarter, time, p_n_ten]
                
                #drive start indicator takes up a row, so if first play, p_n_ten
                # is already set to YES
                p_n_ten = "NO"
                
                #left-er column
                info = r.td.text.upper().encode('ascii', 'ignore')
                
                down = int(info[:1])
                temp.append(down)
                
                loc = info.find('AND')+4
                to_gain = info[ loc : info.find(' ', loc) ]

                ## CONVERT "GOAL" TO NUMBER (find pos first, but add to_gain to temp first)
                pos = info[info.find('AT ')+3 :]
                pos = convert(pos)

                if to_gain.upper() == "GOAL":
                    if pos >= 0:
                        to_gain = pos
                    else:
                        to_gain = pos * -1

                temp.append(to_gain)
                
                temp.append(pos)
                
                ##right-er column
                #detail = r.find_all('td')[1].text.upper().\
                    #replace('\n', '').encode('ascii', 'ignore')
                
                if " DRIVE START " in detail:
                    p_n_ten = "YES"
                    continue
                
                '''
                if " NO PLAY" in detail:
                    #NOTE: I can add penalty yardage if we want
                    temptemp = ['NO PLAY',0,'n/a','n/a']
                    temp = temp + temptemp
                    table.append(temp)
                    continue
                '''
                
                ##Get play type
                play_type = ""
                #if "PENALTY" in detail and "NO PLAY" in detail:
                if "PENALTY" in detail and "DECLINED" not in detail:
                    if "PENALTY DAV" in detail:
                        play_type = "PENALTY DAV"
                    else:
                        play_type = "PENALTY OPP"
                elif "PASS" in detail or "SACK" in detail:
                    play_type = "PASS"
                elif "RUSH" in detail:
                    play_type = "RUN"
                else:
                    play_type = "OTHER" #punt or kick or penalty something
                temp.append(play_type)
                    
                ##Get yards gained
                gained = 0
                if " FOR " in detail and 'NO GAIN' not in detail and "PENALTY" not in play_type:
                    temp_str = detail[detail.find(' FOR '):]
                    x = 1
                    if "LOSS OF " in temp_str:
                        x = -1
                    loc = number_loc(temp_str)
                    gained = temp_str[loc : temp_str.find(' ', loc)]
                    if gained:
                        gained = int(gained) * x
                    else:
                        gained = 0
                temp.append(gained)
                
                ##Get play type
                p1 = 'n/a'; p2 = 'n/a'
                if play_type == "RUN":
                    #p2 = 'n/a' #no passer
                    loc = detail.find("RUSH")
                    p1 = detail[:loc].strip()
                elif play_type == "PASS":
                    if "SACKED" in detail:
                        loc = detail.find("SACKED")
                        p1 = detail[:loc].strip()
                    else:
                        loc = detail.find("PASS")
                        p2 = detail[:loc].strip()
                        
                        loc = detail.find(" TO ") + 4
                        detail2 = detail[loc:]
                        loc_space = find_second(detail2, ' ')
                        loc_period = detail2.rfind('.')
                        end_loc = min([loc_space, loc_period])
                        p1 = detail2[:end_loc]
                temp.append(p1)
                temp.append(p2)
                temp.append(detail.strip().rstrip())
                
                #print temp
                table.append(temp)
    
    headers = ['YEAR','OFF/DEF','DATE','OPPONENT','QTR','TIME','Pand10','DOWN','TO_GAIN','POS',
               'PLAY_TYPE','GAIN','P1','P2','PLAY_DETAIL']
    df = pd.DataFrame(data=table, columns=headers)
    
    return df

'''
Helper designed to append one game's pbp data to the csv designated by filename
'''
def csv(df, firstrun):
    if firstrun:
        df.to_csv(filename,index=False)
    else:
        with open(filename, 'a') as f:
            df.to_csv(f,header=False,index=False)
    

'''
Helper to find the second occurance of a substring in a string and return
its location
'''
def find_second(string, substring):
    first = string.find(substring)
    return string.find(substring, first + 1)
            
'''
So your 32 yard line -> -32
and
Opponent's 27 -> 27

Accepts a string

Returns an integer
'''
def convert(yard):
    if "50" in yard:
        return 50
    
    loc = yard.find('DAV')
    if loc == -1: #opponent's side --> keep positive
        loc = number_loc(yard)
        return int(yard[loc:])
    else: #your side --> make negative
        return int(yard[ loc+3 :  ]) * -1


'''
Helper. Finds location of first digit in a string.
'''
def number_loc(string):
    for i in range(len(string)):
        if string[i].isdigit():
            return i

'''
Function to get all boxscore urls from Davidson's schedule page:

Args:
sch_url - https://davidsonwildcats.com/schedule.aspx?path=football

Returns:
urls - list of each game's boxscores
'''
def get_boxscores(sch_url):
    soup = get_site(sch_url, 0)
    
    base = sch_url[:sch_url[15:].find('/')+15]
    
    holders = soup.find_all('div', {'class':'sidearm-schedule-game-links hide-on-medium-only print-el'})
    print 'Games found:', len(holders)
    
    urls = []
    for game in holders:
        url = game.find('li').a.get('href').encode('ascii','ignore')
        urls.append(base+url)
    
    for x in urls: print x
    return urls

'''
Driver for pbp method which also calls csv helper and get_boxscores to produce
csv file with pbp data from all games in a season.
'''
def run_pbp(sch_url, filename, team):
    links = get_boxscores(sch_url)
    firstrun = True
    for l in links:
        print "\nWorking on:", l
        soup = get_site(l, 0)
        df = get_pbp(soup, team)
        
        csv(df, firstrun)
        firstrun = False
        
    #add win/loss column
    df_old = pd.read_csv(filename)
    df = winloss(df_old)
    df.index.name = 'PLAY_NUM'
    df.to_csv(filename,index=True)


'''
Adds win/loss column to dataframe with guidelines from football coaches

(from defensive perspective)
1st down: Win: 4 yards or less
          Loss: 5 yards or more
2nd down: Win: less than half the yards from 1st down
          Loss: half or more of the yards from 1st down
3rd down: Win: force 4th down
          Loss: give up 1st down
4th down: Win: no 1st down
          Loss: give up 1st down
'''
def winloss(df):
    df['WIN/LOSS'] = 'N/A'
    
    count = 0 #debugging
    last_gain = 0 #keep track of yards gained on 1st down
    for i, row in df.iterrows():
        down = row['DOWN']
        gain = row['GAIN']
        offdef = row['OFF/DEF']
        play_type = row["PLAY_TYPE"]
        to_gain = row['TO_GAIN']
        pos = df.at[i,'POS']
        
        if count > 36:
            pass
        count = count + 1
        
        ##if penalty, see who its against and don't bother looking at the rest
        if 'PENALTY' in play_type:
            if ' DAV' in play_type:
                df.at[i,'WIN/LOSS'] = "L"
            else:
                df.at[i,'WIN/LOSS'] = "W"
            continue

        if down == 1:
            if play_type == "NO PLAY" or play_type == "OTHER":
                df.at[i,'WIN/LOSS'] = "n/a"
                continue            
            if offdef == "OFFENSE":
                if play_type == "NO PLAY" or play_type == "OTHER":
                    df.at[i,'WIN/LOSS'] = "n/a"
                    continue
                if to_gain == "GOAL":
                    if gain >= abs(pos):
                        df.at[i,'WIN/LOSS'] = "W"
                    else:
                        df.at[i,'WIN/LOSS'] = "L"
                else:
                    if gain >= 5:
                        df.at[i,'WIN/LOSS'] = "W"
                        last_gain = gain
                    else:
                        df.at[i,'WIN/LOSS'] = "L"
                        last_gain = gain
            elif offdef == "DEFENSE":
                if to_gain == 'GOAL':
                    if gain >= abs(pos):
                        df.at[i,'WIN/LOSS'] = "L"
                    else:
                        df.at[i,'WIN/LOSS'] = "W"
                else:
                    if gain >= 5:
                        df.at[i,'WIN/LOSS'] = "L"
                        last_gain = gain
                    else:
                        df.at[i,'WIN/LOSS'] = "W"
                        last_gain = gain
        
        elif down == 2:
            if play_type == "NO PLAY" or play_type == "OTHER":
                df.at[i,'WIN/LOSS'] = "n/a"
                continue

            if offdef == "OFFENSE":
                #if they get the 1st down or score a touchdown, win
                if to_gain == 'GOAL':
                    if pos < 0:
                        pos = -1 * pos
                    if gain >= pos:
                        df.at[i,'WIN/LOSS'] = "W"
                    else:
                        df.at[i,'WIN/LOSS'] = "L"
                else:
                    to_gain = int(to_gain)
                    if gain >= to_gain:
                        df.at[i,'WIN/LOSS'] = "W"
                    else:
                        df.at[i,'WIN/LOSS'] = "L"
 
                #if they get more than half the yards they did on 1st down, win
                if gain >= 0.5*last_gain:
                    df.at[i,'WIN/LOSS'] = "W"
                else:
                    df.at[i,'WIN/LOSS'] = "L"
                    
            elif offdef == "DEFENSE":
                if to_gain == 'GOAL':
                    if pos < 0:
                        pos = -1 * pos
                    if gain >= pos:
                        df.at[i,'WIN/LOSS'] = "L"
                    else:
                        df.at[i,'WIN/LOSS'] = "W"
                else:
                    to_gain = int(to_gain)
                    if gain >= to_gain:
                        df.at[i,'WIN/LOSS'] = "L"
                    else:
                        df.at[i,'WIN/LOSS'] = "W"                
                
                if gain >= 0.5*last_gain:
                    df.at[i,'WIN/LOSS'] = "L"
                else:
                    df.at[i,'WIN/LOSS'] = "W"
                    
        #if to_gain is GOAL, convert pos if greater than 50 and see if gain >= to_gain
        elif down == 3 or down == 4:
            if play_type == "NO PLAY" or play_type == "OTHER":
                df.at[i,'WIN/LOSS'] = "n/a"
                continue
            
            if offdef == "OFFENSE":
                if to_gain == 'GOAL':
                    if pos < 0:
                        pos = -1 * pos
                    if gain >= pos:
                        df.at[i,'WIN/LOSS'] = "W"
                    else:
                        df.at[i,'WIN/LOSS'] = "L"
                else:
                    to_gain = int(to_gain)
                    if gain >= to_gain:
                        df.at[i,'WIN/LOSS'] = "W"
                    else:
                        df.at[i,'WIN/LOSS'] = "L"
            elif offdef == "DEFENSE":
                if to_gain == 'GOAL':
                    if pos < 0:
                        pos = -1 * pos
                    if gain >= pos:
                        df.at[i,'WIN/LOSS'] = "L"
                    else:
                        df.at[i,'WIN/LOSS'] = "W"
                else:
                    to_gain = int(to_gain)
                    if gain >= to_gain:
                        df.at[i,'WIN/LOSS'] = "L"
                    else:
                        df.at[i,'WIN/LOSS'] = "W"
        
    #print df.to_string
    df = df.replace(np.NaN, 'n/a')
    return df
    
    
'''
'''
def main():
    ##########
    ##SEASON##
    ##########
    #2017: 'https://davidsonwildcats.com/schedule.aspx?schedule=254'
    # sch_url = raw_input("Paste schedule url: ")
    # team = raw_input("Paste team name (as it appears in play-by-play tab): ").upper()
    # if team == "DAVIDSON": filename = "pbp.csv"
    # else: filename = "pbp-" + team.lower() + ".csv"
    # run_pbp(sch_url, filename, team)
    
    ############
    ##ONE GAME##
    ############
    ##BREVARD 2017: https://davidsonwildcats.com/boxscore.aspx?id=5033&path=football
    url = raw_input("Paste game url: ")
    team = raw_input("Paste team name (as it appears in play-by-play tab): ").upper()
    if team == "DAVIDSON": filename = "pbp.csv"
    else: filename = "pbp-" + team.lower() + ".csv"

    soup = get_site(url, 0)
    df = get_pbp(soup, team)
    df = winloss(df)
    df.index.name = 'PLAY_NUM'
    with open(filename, 'a') as f:
        df.to_csv(f,header=False,index=True)
    
    
    
if __name__ == "__main__":
    main()
    
    print "**done**"
    
    

#NOTE: idk if this works on overtime games; DAV doesn't have OT games to test

#QUESTION - goal to go for first and second down
#QUESTION - when a row has an end-of-play penalty, what to do? Right now, I'm only logging play as PENALTY if
            #penalty is in text (ex: 9 yard rush followed by penalty in Q4 v. brevard)