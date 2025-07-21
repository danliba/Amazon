#!/bin/bash

# Lanzar ambos scripts en segundo plano
bash U_cmems_m.sh &
bash V_cmems_m.sh &

# Esperar a que ambos terminen
wait

echo "Descargas U y V completadas."

