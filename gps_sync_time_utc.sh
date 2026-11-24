#!/bin/bash

# use file on Desktop terminal with: bash FILENAME
# only works if GPS sensor is outdoors or close to windows

DEFAULT_DEVICE="/dev/serial/by-id/usb-u-blox_AG_-_www.u-blox.com_u-blox_GNSS_receiver-if00"
if [[ ! -e "$DEFAULT_DEVICE" ]]; then
	DEFAULT_DEVICE="/dev/ttyACM0"
fi
DEVICE="${1:-$DEFAULT_DEVICE}"
TIMEOUT=60 # seconds
START=$(date +%s)

if [ ! -r "$DEVICE" ]; then
	echo "GPS device not readable: $DEVICE" >&2
	exit 1
fi

stty -F "$DEVICE" raw -echo 2>/dev/null || true
exec 3< "$DEVICE"
trap 'exec 3<&-' EXIT

echo "Waiting for GPS fix ..."

# Read until valid RMC value, GPS fix
while true; do
	NOW=$(date +%s)
	if (( NOW - START > TIMEOUT )); then
		echo "No GPS fix after $TIMEOUT seconds."
		exit 1
	fi

	if ! IFS= read -r -t 2 LINE <&3; then
		continue
	fi
	LINE=${LINE%$'\r'}

	# check if there is an RMC sentence ($GNRMC or $GPRMC)
	if [[ "$LINE" == \$G[NP]RMC* ]]; then
		IFS=',' read -r _ TIME STATUS _ _ _ _ _ _ DATE _ <<< "$LINE"

		# only proceed if data is valid
		if [[ "$STATUS" == "A" && "$TIME" =~ ^[0-9]{6} && "$DATE" =~ ^[0-9]{6}$ ]]; then
			echo "GPS fix acquired."
			break
		else
			echo "... no fix yet (RMC status: ${STATUS:-unknown})"
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

echo "Setting system time to UTC: ${YYYY}-${MO}-${DD} ${HH}:${MM}:${SS}"

# Set system time (UTC)
sudo date -u -s "${YYYY}-${MO}-${DD} ${HH}:${MM}:${SS}"
echo "Done."
