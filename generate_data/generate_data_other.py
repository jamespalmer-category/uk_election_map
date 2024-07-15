import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Union, Optional
import pandas as pd
import argparse

def find_links_to_data() -> List[Dict[str, str]]:
    # note - the links hold the ons_id of the constituency
    url = "https://www.bbc.com/news/politics/constituencies"
    response = requests.get(url)
    html_content = response.content
    soup = BeautifulSoup(html_content, 'html.parser')

    links = soup.find_all('a')
    return [{"ons_id":link.get('href')[-9:],
             "constituency_name":link.text,
             "url":'https://www.bbc.co.uk'+link.get('href')} for link in links[60:710]]

def find_vote_data(url:str) -> List[Dict[str, Union[str,int]]]:
    response = requests.get(url)
    html_content = response.content
    soup = BeautifulSoup(html_content, 'html.parser')
    table_entries_19=soup.find('div', class_="ge2019-constituency-result")
    turnout=sum([int(entry.text.replace(',','')) for i, entry in enumerate(table_entries_19.find_all('span',class_="ge2019-constituency-result__details-value")) if i % 3 == 0])
    return ({'turnout':turnout,
             'registered_voters':int(soup.find_all('span',class_="ge2019-constituency-result-turnout__value")[1].text.replace(',','')),
             'turnout_change':soup.find_all('span',class_="ge2019-constituency-result-turnout__value")[3].text.strip(),
             'win_margin':int(soup.find_all('span',class_="ge2019-constituency-result-turnout__value")[0].text.replace(',',''))}
            ,[{"Party":table_entries_19.find_all('span',class_="ge2019-constituency-result__party-name")[i].text, 
      "Candidate":table_entries_19.find_all('span', class_="ge2019-constituency-result__candidate-name")[i].text,
      "Votes":int(table_entries_19.find_all('span',class_="ge2019-constituency-result__details-value")[i*3].text.replace(',', '')),
      "Vote Share":float(table_entries_19.find_all('span',class_="ge2019-constituency-result__details-value")[i*3+1].text.replace('%', '')),
      "Share Change": table_entries_19.find_all('span', class_="ge2019-constituency-result__details-value")[i*3+2].text.strip()}
     for i in range(len(table_entries_19.find_all('span',class_="ge2019-constituency-result__party-name")))])

#Just used in dict_preprocess
def ordinal(n: int) -> str:
    if 11 <= (n % 100) <= 13:
        suffix = 'th'
    else:
        suffix = ['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]
    return str(n) + suffix

#Just used in dict_to_df in a list comprehension
def dict_preprocess(cons_dict:Dict[str, Union[str,int]],
                    top_n:Optional[int] = None):

    if not top_n:
        top_n = len(cons_dict["breakdown"]) 

    new_dict = {}
    new_dict["ons_id"] = cons_dict['ons_id']
    new_dict["name"] = cons_dict['constituency_name']
    new_dict["turnout"] = cons_dict["turnout"]
    new_dict["registered_voters"] = cons_dict["registered_voters"]
    new_dict["turnout_change"] = cons_dict["turnout_change"]
    for i, candidate in enumerate(cons_dict['breakdown'][:top_n]):
        new_dict[f"{ordinal(i+1)}_place_party"] = candidate['Party']
        new_dict[f"{ordinal(i+1)}_place_candidate"] = candidate['Candidate']
        new_dict[f"{ordinal(i+1)}_place_votes"] = candidate['Votes']

    return new_dict

def dict_to_df(cons_dicts):
    return pd.DataFrame.from_dict([dict_preprocess(cons_dict) for cons_dict in cons_dicts])

def df_cleanup(df):
    df['total_votes'] = df.apply(lambda x: sum([x[column] for column in df.columns if 'votes' in column and type(x[column]) == int]), axis=1)
    df['turnout_change'] = df['turnout_change'].apply(lambda x: float(x[1:].replace('%','')) if x[0]=='+' else -1*float(x[1:].replace('%','')))

    new_order = list(df.columns)[:5]+list(df.columns)[-2:]+list(df.columns)[5:-2]
    return df[new_order]

def main(filepath:str) -> None:
    constituency_dicts = find_links_to_data()
    for constituency in constituency_dicts:
        print(constituency)
        turnout, breakdown = find_vote_data(constituency['url'])
        for k,v in turnout.items():
            constituency[k] = v
        constituency['breakdown'] = breakdown
    df = dict_to_df(constituency_dicts)
    df = df_cleanup(df)
    df.to_csv(filepath, index=False)

if __name__ =='__main__':
    
    parser = argparse.ArgumentParser(description="Process a file path.")
    parser.add_argument('filepath', type=str, help="The path to put the csv after")
    args = parser.parse_args()
    main(args.filepath)