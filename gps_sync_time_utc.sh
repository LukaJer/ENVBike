#!/bin/bash

# use file on Desktop terminal with: bash FILENAME
# only works if GPS sensor is outdoors or close to windows

DEVICE="/dev/ttyACM0"
TIMEOUT=60 # seconds
START=$(date +%s)

echo "Waiting for GPS fix ..."

# Read until valid RMC value, GPS fix
while true; do
	NOW=$(date +%s)
	if (( NOW - START > TIMEOUT )); then
		echo "No GPS fix after $TIMEOUT seconds."
		exit 1
	fi	

	LINE=$(head -n 1 < "$DEVICE")

	# check if ther is a RMC sentence
	if [[ "$LINE" == \$GNRMC* ]]; then
		STATUS=$(echo "$LINE" | cut -d',' -f3)

		# only proceed if data is valid
		if [[ "$STATUS" == "A" ]]; then
			echo "GPS fix acquired."
			TIME=$(echo "$LINE" | cut -d',' -f2)
			DATE=$(echo "$LINE" | cut -d',' -f10)
			break
		else
			echo "... no fix yet (RMC status V)"
		fi
	fi
done

# Parse time
HH=${TIME:0:2}
MM=${TIME:2:2}
SS=${TIME:4:2}

# Parse date
DD=${DATE:0:2}
MO=${DATE:2:2}
YY=${DATE:4:2}
YYYY="20$YY"

# convert month to name
MONTH=$(date -d "$YYYY-$MO-01" "+%b" | tr '[:lower:]' '[:upper:]')

echo "Setting system time to UTC: ${DD} ${MONTH} ${YYYY} ${HH}:${MM}:${SS}"

# Set system time (UTC)
sudo date -s "${DD} ${MONTH} ${YYYY} ${HH}:${MM}:${SS}"
echo "Done."
