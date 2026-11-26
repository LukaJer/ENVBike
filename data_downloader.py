import requests
import json

# executes a download of measurement data for given species time and day
# open terminal then cd Desktop
# python3 data_downloader.py after adjusting the file
# at the moment there is a serverside limit of 5050 lines
# if you have more than that just split up via the time input

start_time = '2026-02-24T14:23:00'
end_time = '2026-03-24T14:52:00'
species = 'CH4' # 'CO2'



# there is no necessary change after this point
ip_address = '192.168.0.101'
port = '5000'
url = f'http://{ip_address}:{port}/measurement/gas'

query_params = {
	'with-location': 1,
	'start': start_time,
	'end': end_time,
	'type': species,
	'limit': '5050'
}

# generate safe filename
safe_date = start_time.replace(':', '-')
filename = f'mu_{species}_{safe_date}.json'

try:
	response = requests.get(url, params=query_params, stream=True)
	response.raise_for_status()
	
	# make it column data and not one line
	#data = response.json()
	
	with open(filename, 'wb') as f:
		for chunk in response.iter_content(chunk_size=8192):
			f.write(chunk)
		
		
	print(f'Saved data to: {filename}.')

except requests.exceptions.RequestException as e:
	print(f'Download failed: {e}')
