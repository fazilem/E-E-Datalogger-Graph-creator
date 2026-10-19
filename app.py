import io
from datetime import datetime, date, time
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import MultipleLocator, FuncFormatter, FixedLocator
from matplotlib.backends.backend_pdf import PdfPages
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title='Accutech Environmental Data Logger', layout='wide', page_icon='🌡️')
st.title('Environmental Monitoring Dashboard')
st.caption('Accutech Automation | Temperature · Relative Humidity · Atmospheric Pressure')

PARAMS = {
 'Temperature': {'column':'Temperature', 'unit':'°C','color':'#f15a24','legend':'Temperature [°C] Avg','step':0.5},
 'Relative Humidity': {'column':'Relative Humidity','unit':'%','color':'#00b9ee','legend':'Relative Humidity [%] Avg','step':1.0},
 'Atmospheric Pressure': {'column':'Atmospheric Pressure','unit':'hPa','color':'#8bea22','legend':'Relative Air Pressure [hPa] Avg','step':0.5},
}

def read_csv(file):
    raw=file.getvalue()
    attempts=[]
    for enc in ('utf-8-sig','utf-16','cp1252'):
        for sep in (';',',','\t'):
            try:
                df=pd.read_csv(io.BytesIO(raw),sep=sep,header=None,encoding=enc,dtype=str,engine='python',on_bad_lines='skip')
                # Some exports wrap each entire semicolon-delimited row in CSV quotes.
                if df.shape[1] == 1:
                    split=df.iloc[:,0].astype(str).str.split(sep,regex=False,expand=True)
                    if split.shape[1] >= 4:
                        df=split.iloc[:,:4].apply(lambda c: c.str.strip().str.strip('\"'))
                if df.shape[1]<4: continue
                # Files may contain a header row; date parsing drops it safely.
                dt=pd.to_datetime(df.iloc[:,0].str.strip().str.strip('"'),errors='coerce',format='mixed',dayfirst=False)
                if dt.notna().sum()<2: continue
                out=pd.DataFrame({'Timestamp':dt})
                for idx,key in enumerate(PARAMS):
                    out[key]=pd.to_numeric(df.iloc[:,idx+1].str.strip().str.replace(',','.',regex=False),errors='coerce')
                out=out.dropna(subset=['Timestamp']).sort_values('Timestamp').drop_duplicates('Timestamp')
                if out[list(PARAMS)].notna().sum().sum()==0: continue
                return out.reset_index(drop=True)
            except Exception as exc: attempts.append(str(exc))
    raise ValueError('Expected at least four columns: timestamp; temperature; humidity; atmospheric pressure. CSV delimiter may be ; or , or tab.')

def draw_pdf_page(df, key, logger_name, print_time):
    p=PARAMS[key]
    fig=plt.figure(figsize=(8.27,11.69),facecolor='white')
    # Tall, narrow, framed chart to match the supplied logger PDFs.
    ax=fig.add_axes([0.155,0.115,0.735,0.765])
    vals=df[key].dropna()
    if vals.empty: raise ValueError(f'No measurements available for {key}')
    ax.plot(df['Timestamp'],df[key],color=p['color'],linewidth=0.65,solid_joinstyle='round')
    ax.set_xlim(df.Timestamp.min(),df.Timestamp.max())
    vmin=float(vals.min());vmax=float(vals.max())
    # Choose a readable Y-axis spacing for the available plot height.
    # Pressure can span much more than 0.5 hPa over a fortnight.
    base_step=p['step']
    span=max(vmax-vmin,base_step)
    target_step=span/12.0
    nice_multipliers=(1,2,2.5,4,5,10,20,25,40,50,100)
    step=next((base_step*m for m in nice_multipliers if base_step*m>=target_step),base_step*200)
    lo=np.floor((vmin-0.08*max(vmax-vmin,step))/step)*step
    hi=np.ceil((vmax+0.08*max(vmax-vmin,step))/step)*step
    if hi<=lo: hi=lo+step*2
    ax.set_ylim(lo,hi)
    ax.yaxis.set_major_locator(MultipleLocator(step))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x,pos: f'{x:g}'))
    ax.tick_params(axis='y',labelsize=7,colors=p['color'],labelrotation=90,length=3,pad=2)
    ax.tick_params(axis='x',which='major',labelsize=6.5,colors='#777777',length=3,pad=2,rotation=0)
    # Use explicit calendar-day ticks rather than automatic locators: prevents
    # thousands of overlapping labels in dense 10-minute logger exports.
    first = df.Timestamp.min().normalize()
    last = df.Timestamp.max().normalize()
    day_count = max(1, (last - first).days)
    interval = max(1, int(np.ceil(day_count / 7)))
    ticks = pd.date_range(first, last, freq=f'{interval}D')
    tick_numbers = mdates.date2num(ticks.to_pydatetime())
    ax.xaxis.set_major_locator(FixedLocator(tick_numbers))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d/%Y'))
    ax.xaxis.set_minor_locator(FixedLocator([]))
    ax.tick_params(axis='x', which='minor', bottom=False, labelbottom=False)
    ax.grid(False, which='both')
    ax.grid(axis='x', which='major', color='#e9e9e9',linewidth=0.55)
    ax.grid(axis='y',visible=False)
    for side in ax.spines: ax.spines[side].set_color('#aaaaaa');ax.spines[side].set_linewidth(0.65)
    ax.text(-0.055,0.01,p['unit'],transform=ax.transAxes,rotation=90,color=p['color'],fontsize=8,va='bottom')
    fig.text(0.52,0.954,logger_name,ha='center',fontsize=8,color='#777777')
    left,right=0.11,0.90
    import matplotlib.patches as patches
    border=patches.FancyBboxPatch((left,0.101),right-left,0.801,boxstyle='round,pad=0.003,rounding_size=0.005',transform=fig.transFigure,fill=False,edgecolor='#999999',linewidth=0.9)
    fig.patches.append(border)
    start=df.Timestamp.min().strftime('%m/%d/%Y %I:%M:%S %p')
    end=df.Timestamp.max().strftime('%m/%d/%Y %I:%M:%S %p')
    fig.text(left+0.01,0.888,f'({start} - {end})',fontsize=8,color='#333333')
    fig.text(left+0.012,0.869,'━━',fontsize=9,color=p['color'])
    fig.text(left+0.053,0.869,p['legend'],fontsize=7,color='#333333',bbox={'facecolor':'white','edgecolor':'#aaaaaa','linewidth':0.4,'pad':1.3})
    fig.text(0.50,0.073,'Page 1/1',fontsize=7,ha='center',color='#888888')
    fig.text(0.90,0.073,print_time.strftime('%m/%d/%Y %I:%M:%S %p'),fontsize=7,ha='right',color='#888888')
    return fig

uploaded=st.file_uploader('Upload data logger CSV',type=['csv','txt'])
if uploaded is None:
    st.info('Upload your CSV file to display the three graphs and generate printable PDF reports.')
    st.code('6/1/2026 12:00:00 AM;27.0;57.3;1002.4',language='text')
    st.stop()
try: data=read_csv(uploaded)
except Exception as exc: st.error(f'Cannot read CSV: {exc}');st.stop()

with st.sidebar:
    st.header('Report settings')
    logger=st.text_input('Data logger name','Network Data-Logger 04A7/')
    st.write('Available data:',data.Timestamp.min().strftime('%d %b %Y %H:%M'),'to',data.Timestamp.max().strftime('%d %b %Y %H:%M'))
    dates=st.date_input('Date range',(data.Timestamp.min().date(),data.Timestamp.max().date()),min_value=data.Timestamp.min().date(),max_value=data.Timestamp.max().date())
    st.caption('Select dates to filter data. End date includes the entire day.')
    chart_height=st.slider('Dashboard graph height',300,750,450,25)
    st.divider()
    st.subheader('PDF printing date / time')
    automatic_print_time=st.checkbox('Use current date and time',value=True)
    if automatic_print_time:
        print_time=datetime.now()
        st.caption('PDF footer will show the current computer date and time.')
    else:
        manual_print_date=st.date_input('Printing date',value=date.today(),format='DD/MM/YYYY',key='manual_print_date')
        manual_print_clock=st.time_input('Printing time',value=datetime.now().time().replace(second=0,microsecond=0),step=60,key='manual_print_clock')
        print_time=datetime.combine(manual_print_date,manual_print_clock)
        st.caption('This date/time appears in the bottom-right PDF footer only. CSV timestamps are unchanged.')

if not isinstance(dates,(list,tuple)) or len(dates)!=2: st.warning('Select both start and end dates.');st.stop()
start_date,end_date=dates
filtered=data[(data.Timestamp.dt.date>=start_date)&(data.Timestamp.dt.date<=end_date)].copy()
if filtered.empty: st.warning('No measurements in selected date range.');st.stop()

st.success(f'{len(filtered):,} records loaded · {filtered.Timestamp.min():%d %b %Y %H:%M} to {filtered.Timestamp.max():%d %b %Y %H:%M}')
summary=[]
for name,p in PARAMS.items():
    v=filtered[name].dropna()
    summary.append({'Parameter':name,'Minimum':round(v.min(),2) if len(v) else None,'Maximum':round(v.max(),2) if len(v) else None,'Average':round(v.mean(),2) if len(v) else None,'Unit':p['unit']})
st.dataframe(pd.DataFrame(summary),hide_index=True,use_container_width=True)

for name,p in PARAMS.items():
    st.subheader(f'{name} [{p["unit"]}]')
    fig=go.Figure()
    fig.add_trace(go.Scatter(x=filtered.Timestamp,y=filtered[name],mode='lines',name=p['legend'],line={'color':p['color'],'width':1.25},connectgaps=False))
    fig.update_layout(height=chart_height,margin={'l':35,'r':20,'t':20,'b':35},hovermode='x unified',xaxis_title='Date / Time',yaxis_title=p['unit'],plot_bgcolor='white')
    fig.update_xaxes(showgrid=True,gridcolor='#eeeeee',rangeslider_visible=False)
    fig.update_yaxes(showgrid=True,gridcolor='#f2f2f2')
    st.plotly_chart(fig,use_container_width=True,config={'displaylogo':False,'toImageButtonOptions':{'format':'png','scale':3}})

st.divider()
st.header('Print / Download PDF Reports')
st.info('Click a PDF button below, open the downloaded PDF, then press Ctrl + P to print. Each report is formatted for A4 portrait paper.')
st.caption(f'PDF footer printing date/time: {print_time:%m/%d/%Y %I:%M:%S %p}')
cols=st.columns(4)
for i,name in enumerate(PARAMS):
    with cols[i]:
        if filtered[name].notna().any():
            figure=draw_pdf_page(filtered,name,logger,print_time)
            buffer=io.BytesIO();figure.savefig(buffer,format='pdf',facecolor='white');plt.close(figure)
            st.download_button(f'Download {name} PDF',buffer.getvalue(),file_name=f'{name.lower().replace(" ","_")}_report.pdf',mime='application/pdf',use_container_width=True)
with cols[3]:
    buffer=io.BytesIO()
    with PdfPages(buffer) as pdf:
        for name in PARAMS:
            if filtered[name].notna().any():
                figure=draw_pdf_page(filtered,name,logger,print_time)
                pdf.savefig(figure,facecolor='white');plt.close(figure)
    st.download_button('Download all 3 PDF pages',buffer.getvalue(),file_name='environmental_monitoring_all.pdf',mime='application/pdf',use_container_width=True)

st.download_button('Download filtered CSV',filtered.to_csv(index=False).encode('utf-8'),file_name='filtered_environment_data.csv',mime='text/csv')
