'''
Reads offensive drive output of WLU offensive season as a human would to produce
a text summary of the data for each game

Author: Matt Wang
'''

import pandas as pd

FILENAME = "drives.csv"

def summarize():
    df = pd.read_csv(FILENAME)
    
    ##get a list of the opponents
    opponents = df['opponent'].unique()
    print "Opponents:", opponents
    
    ##iterate over each opponent to calculate stats for each game
    for opp in opponents:
        #game_df = df[(df.opponent == opp) & (df.offdef == "OFFENSE")]
        game_df = df[df.opponent == opp]
        print game_df.to_string()
        
        n_drives = game_df.shape[0]
        point_drives = 0
        n_two_first_downs = 0
        point_two_first_downs = 0
        n_fourth_attempted = 0
        fourth_converted = 0
        point_fourth_attempted = 0
        for index, row in game_df.iterrows():
            if row['points'] != 0:
                point_drives = point_drives + 1
                
            if row['first_downs_earned'] >= 2:
                n_two_first_downs = n_two_first_downs + 1
                if row['points'] != 0:
                    point_two_first_downs = point_two_first_downs + 1
            
            if row['fourth_attempted'] == True:
                n_fourth_attempted = n_fourth_attempted + 1
                if row['fourth_converted'] == True:
                    fourth_converted = fourth_converted + 1
                if row['points'] != 0:
                    point_fourth_attempted = point_fourth_attempted + 1
                    
        print n_drives, point_drives, n_two_first_downs, point_two_first_downs, n_fourth_attempted, point_fourth_attempted, fourth_converted
        print "\n"
        
        with open('offensive-summary.txt', 'a') as file:
            file.write("OPPONENT: " + opp + "\n\n" + str(n_drives) + \
                       " total offensive drives\n" + str(point_drives) + \
                       " drives resulting in points\n" + str(round(float(point_drives)/float(n_drives),3)*100) + "%\n" + \
                       "\n" + str(n_two_first_downs) + "/" + str(n_drives) + \
                       " drives had two consecutive first downs\nOf these, " + \
                       str(point_two_first_downs) + "/" + str(n_two_first_downs) + \
                       " drives resulted in points off of two consecutive first downs" + \
                       "\n\n" + str(fourth_converted) + "/" + str(n_fourth_attempted) + " on fourth down conversions\n" + \
                       str(point_fourth_attempted) + " converted fourth down(s) resulting in points" + \
                       "\n\n\n")
    

def main():
    summarize()
    
if __name__ == "__main__":
    main()