#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
import datetime
import dash
import dash_table
import dash_core_components as dcc
import dash_html_components as html
#import dash_bootstrap_components as dbc
from dash.dependencies import Input,Output
import re


# In[2]:


LatLong=pd.read_csv('https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat',header=None,
                names=['Airport ID','Name','City','Country','IATA','ICAO','Latitude','Longitude','Altitude','Timezone','DST',
                      'Tz ','Type','Source'])

url = "https://skyscanner-skyscanner-flight-search-v1.p.rapidapi.com/apiservices/reference/v1.0/countries/en-US"

headers = {
    'x-rapidapi-host': "skyscanner-skyscanner-flight-search-v1.p.rapidapi.com",
    'x-rapidapi-key': "161a3da445mshae947b44fdb73a5p1be27fjsn1227b9e114ad"
    }
r=requests.get(url,headers=headers)
j=r.json()
Countries=pd.DataFrame(j['Countries'])
Countries['OD']=Countries.Code.apply(lambda x: x+'-sky')

url = "https://skyscanner-skyscanner-flight-search-v1.p.rapidapi.com/apiservices/reference/v1.0/currencies"

headers = {
    'x-rapidapi-host': "skyscanner-skyscanner-flight-search-v1.p.rapidapi.com",
    'x-rapidapi-key': "161a3da445mshae947b44fdb73a5p1be27fjsn1227b9e114ad"
    }
r=requests.get(url,headers=headers)
j=r.json()
Currencies=pd.DataFrame(j['Currencies']).drop(['Symbol', 'ThousandsSeparator', 'DecimalSeparator','SymbolOnLeft',
                                               'SpaceBetweenAmountAndSymbol', 'RoundingCoefficient','DecimalDigits'],axis=1)
Currency=pd.read_excel('Currency.xlsx')

Currencies['Currency']=Currencies.Code.apply(lambda x: [y for y in Currency.loc[Currency['ISO-4217']==x,'Currency']][0] 
                                             if len([y for y in Currency.loc[Currency['ISO-4217']==x,'Currency']])>0 else np.nan)
Currencies.dropna(inplace=True)


# In[ ]:


app=dash.Dash(__name__)
app.config['suppress_callback_exceptions']=True

# Styling

Heading={'background':'#e76f51','text-align':'center','font-weight':'bold','color':'#f1faee'}
Page_Bg={'background':'#e76f51'}

maxdate=datetime.datetime.today().date()+datetime.timedelta(days=59)
mindate=datetime.datetime.today().date()+datetime.timedelta(days=1)

app.layout=html.Div([
    html.Div([
        html.H1('SIMPLE FLIGHT RATES CHECKING',style=Heading),
        html.Div([
            html.Div(dcc.Dropdown(id='Origin',options=[{'label':x,'value':x} for x in Countries['Name']],multi=False,
                                 placeholder='Select Origin',searchable=True,value='India'),className='two columns'),
            html.Div(dcc.Dropdown(id='Destination',options=[{'label':x,'value':x} for x in Countries['Name']],multi=False,
                                 placeholder='Select Destination',searchable=True,value='Germany'),className='two columns'),
            html.Div(dcc.DatePickerSingle(id='Departure Date',min_date_allowed=mindate,max_date_allowed=maxdate,
                                         placeholder='Departure Date',date=mindate),className='two columns'),
            html.Div(dcc.Dropdown(id='Currency',options=[{'label':x,'value':x} for x in Currencies['Currency']],multi=False,
                                 placeholder='Select Currency',searchable=True,clearable=True,value='Indian rupee'),className='two columns')
        ],className='row')],style=Page_Bg),
    html.Div(dcc.Graph(id='Graph-Container'),style=Page_Bg),
    html.Div([dash_table.DataTable(id='Quotation',style_cell={'text_Align':'left','backgroundColor':'#e9c46a','font_size':'18px','border':'1px #e9c46a'},
                                   style_header={'backgroundColor':'#e76f51','fontWeight':'bold','border':'1px  #e76f51'},
                                   style_as_list_view=True,row_selectable='single',selected_rows=[]),
             dcc.Textarea(id='TextArea',style={'width':'100%','height':100,'backgroundColor':'#e76f51',
                                               'color':'white'})],style=Page_Bg),
    html.Div(dcc.Store(id='Memory'),style=Page_Bg),
   
])

@app.callback(
[Output('Quotation','data'),
 Output('Quotation','columns'),
Output('Memory','data'),
Output('TextArea','value')],
[Input('Origin','value'),
Input('Currency','value'),
Input('Destination','value'),
Input('Departure Date','date')]
)

def Table(Ori,Curr,Desti,date):
    
    if Ori is not None and Desti is not None and Curr is not None and date is not None:
        country=[x for x in Countries.loc[Countries.Name==Ori,'Code']][0]
        currency=[x for x in Currencies.loc[Currencies.Currency==Curr,'Code']][0]
        locale='en-US'
        originplace=[x for x in Countries.loc[Countries.Name==Ori,'OD']][0]
        destinationplace=[x for x in Countries.loc[Countries.Name==Desti,'OD']][0]
        OPD=datetime.datetime.strptime(re.split('T| ', date)[0], '%Y-%m-%d')
        outboundpartialdate=OPD.strftime('%Y-%m-%d')
        inbountpartialdate=''
        url = "https://skyscanner-skyscanner-flight-search-v1.p.rapidapi.com/apiservices/browseroutes/v1.0/"+country+"/"+currency+"/"+locale+"/"+originplace+"/"+ destinationplace +"/" + outboundpartialdate

        querystring = {"inboundpartialdate":inbountpartialdate}

        headers = {
            'x-rapidapi-host': "skyscanner-skyscanner-flight-search-v1.p.rapidapi.com",
            'x-rapidapi-key': "161a3da445mshae947b44fdb73a5p1be27fjsn1227b9e114ad"
            }

        r = requests.get(url, headers=headers, params=querystring)

        j=r.json()
        Quotes=pd.DataFrame(j['Quotes'])
        if Quotes.empty==False:
            Quotes['QuoteDateTime']=pd.to_datetime(Quotes['QuoteDateTime'])
            OutboundLeg=pd.DataFrame([x for x in Quotes['OutboundLeg']])
            OutboundLeg['DepartureDate']=pd.to_datetime(OutboundLeg['DepartureDate'])
            Carriers=pd.DataFrame(j['Carriers'])
            Carriers.set_index('CarrierId',inplace=True)
            Places=pd.DataFrame(j['Places'])
            Places.set_index('PlaceId',inplace=True)
            Quotes=Quotes.join(OutboundLeg)
            Quotes.drop(['OutboundLeg','QuoteId'],inplace=True,axis=1)
            CarrierIds=[]
            for i in range(len(Quotes['CarrierIds'])):
                CarrierIds=CarrierIds+[Quotes['CarrierIds'][i][0]]
            Quotes['CarrierIds']=CarrierIds
            Quotes['CarrierIds']=Quotes['CarrierIds'].apply(lambda x: Carriers.loc[x][0])
            Quotes['Origin']=Quotes['OriginId'].apply(lambda x: Places.loc[x,'CityName'])
            Quotes['Destination']=Quotes['DestinationId'].apply(lambda x: Places.loc[x,'CityName'])
            Quotes['OriginId']=Quotes['OriginId'].apply(lambda x: Places.loc[x,'IataCode'])
            Quotes['DestinationId']=Quotes['DestinationId'].apply(lambda x: Places.loc[x,'IataCode'])
            Quotes.drop(['QuoteDateTime','DepartureDate'],axis=1,inplace=True)

            d=Quotes.to_dict('records')
            values=''         
            columns=[{'name':x,'id':x} for x in Quotes.columns]
            data=Quotes.to_dict('records')
            
            return data,columns,d,values
        else: 
            d=[]
            columns=None
            data=None
            values='No Flights scheduled from '+Ori+' to '+Desti+' on '+str(date)
            fig = go.Figure(go.Scattermapbox(mode = "markers",lon = [10, 20, 30],lat = [10, 20,30],marker = {'size': 1}))
            fig.update_layout(margin ={'l':0,'t':0,'b':0,'r':0},mapbox = {'style': "stamen-terrain",'center': {'lon': 0, 'lat': 0},
                                                              'zoom': 1})
            return data,columns,d,values
        
    else:
        d=None
        columns=None
        data=None
        
        values=''
        Comments=['\nPlease select your Origin location','\nPlease select your Destination location',
                 '\nPlease select the Currency in which your Flight Rates need to be','\nPlease select your Departure Date']
        Variables=[Ori,Desti,Curr,date]

        for i,j in zip(Variables,Comments):
            if i is None:
                values+=j
                
        return data,columns,d,values
    
    
@app.callback(
Output('Graph-Container','figure'),
[Input('Quotation', 'selected_rows'),
Input('Memory','data')])

def Update_Graph(row_id,data):
    
    if data is not None and len(row_id)>0:
        Quotes=pd.DataFrame(data)
        dff=pd.DataFrame()
        try:
            for i in row_id:
                dff=Quotes.iloc[i]

            Origin=dff['OriginId']
            Destination=dff['DestinationId']
            OriginDf=pd.DataFrame(Quotes.loc[(Quotes.OriginId==Origin) & (Quotes.DestinationId==Destination),'OriginId']).rename(columns={'OriginId':'IATA'})
            DestinationDf=pd.DataFrame(Quotes.loc[(Quotes.OriginId==Origin) & (Quotes.DestinationId==Destination),'DestinationId']).rename(columns={'DestinationId':'IATA'})
            FlightRoute=pd.concat([OriginDf,DestinationDf])
            FlightRoute['AirportName']=FlightRoute['IATA'].apply(lambda x:[y for y in LatLong.loc[LatLong.IATA==x,'Name']][0])
            FlightRoute['Country']=FlightRoute['IATA'].apply(lambda x:[y for y in LatLong.loc[LatLong.IATA==x,'Country']][0])
            FlightRoute['City']=FlightRoute['IATA'].apply(lambda x:[y for y in LatLong.loc[LatLong.IATA==x,'City']][0])
            FlightRoute['Latitude']=FlightRoute['IATA'].apply(lambda x:[y for y in LatLong.loc[LatLong.IATA==x,'Latitude']][0])
            FlightRoute['Longitude']=FlightRoute['IATA'].apply(lambda x:[y for y in LatLong.loc[LatLong.IATA==x,'Longitude']][0])

            lat=[x for x in FlightRoute['Latitude']]
            lon=[x for x in FlightRoute['Longitude']]

            HoverInfo=FlightRoute.drop(['IATA','Latitude','Longitude'],axis=1)
            HoverInfo=HoverInfo.to_dict('records')

            fig=go.Figure(go.Scattermapbox(mode = 'markers+lines',lat=lat,lon=lon,text=HoverInfo,hoverinfo='text',marker = {'size': 10,'color':'red'}))
            fig.update_layout(margin ={'l':0,'t':0,'b':0,'r':0},mapbox = {'style': "stamen-terrain",'zoom': 1,
                                                              'center':{'lat':0,'lon':0}})
        except IndexError:
            fig = go.Figure(go.Scattermapbox(mode = "markers",lon = [10, 20, 30],lat = [10, 20,30],marker = {'size': 1}))
            fig.update_layout(margin ={'l':0,'t':0,'b':0,'r':0},mapbox = {'style': "stamen-terrain",'center': {'lon': 0, 'lat': 0},
                                                              'zoom': 1})
        return fig
    else: 
        fig = go.Figure(go.Scattermapbox(mode = "markers",lon = [10, 20, 30],lat = [10, 20,30],marker = {'size': 1}))
        fig.update_layout(margin ={'l':0,'t':0,'b':0,'r':0},mapbox = {'style': "stamen-terrain",'center': {'lon': 0, 'lat': 0},
                                                              'zoom': 1})
        return fig
    
if __name__=='__main__':
    app.run_server(debug=True,use_reloader=False,port=4050)


# In[ ]:




