#!/bin/bash

################################################################################
# Server Startup Script
# This script starts the animation server, Vite client, and GPT-SoVITS server
################################################################################

#------------------------------------------------------------------------------
# USER CONFIGURATION - Modify these paths for your environment
#------------------------------------------------------------------------------

# Project paths
PROJECT_ROOT="/home/rayenfeng/riko_project_v1"
SOVITS_ROOT="/home/rayenfeng/GPT-SoVITS"

# Virtual environment paths
VENV_PROJECT="${PROJECT_ROOT}/.venv"
VENV_SOVITS="${SOVITS_ROOT}/.venv"

# Server directories
SERVER_DIR="${PROJECT_ROOT}/server"
CLIENT_DIR="${PROJECT_ROOT}/client"

# GPT-SoVITS configuration
SOVITS_CONFIG="${SOVITS_ROOT}/GPT_SoVITS/configs/tts_infer.yaml"
SOVITS_HOST="127.0.0.1"
SOVITS_PORT="9880"

# Optional: Uncomment to enable second GPT-SoVITS server
# SOVITS_CONFIG_2="${SOVITS_ROOT}/GPT_SoVITS/configs/tts_infer_alt.yaml"
# SOVITS_PORT_2="9881"

# Startup delay (seconds to wait for ports to free after killing processes)
STARTUP_DELAY=4

#------------------------------------------------------------------------------
# SCRIPT LOGIC - No need to modify below this line
#------------------------------------------------------------------------------

echo "========================================="
echo "Starting Server Stack"
echo "========================================="

# Kill existing processes
echo "→ Stopping existing servers..."
pkill -f "python3 api_v2.py"
pkill -f "server.py"
pkill -f "npx vite"
pkill -f "vite"

echo "→ Waiting ${STARTUP_DELAY} seconds for ports to free up..."
sleep "$STARTUP_DELAY"

# Start animation server
echo "→ Starting animation server..."
bash -c "source ${VENV_PROJECT}/bin/activate && cd ${SERVER_DIR} && python server.py" &

# Start Vite client
echo "→ Starting Vite client..."
bash -c "cd ${CLIENT_DIR} && npx vite" &

# Start GPT-SoVITS server
echo "→ Starting GPT-SoVITS server on ${SOVITS_HOST}:${SOVITS_PORT}..."
bash -c "source ${VENV_SOVITS}/bin/activate && cd ${SOVITS_ROOT} && python3 api_v2.py -a ${SOVITS_HOST} -p ${SOVITS_PORT} -c ${SOVITS_CONFIG}" &

# Optional: Start second GPT-SoVITS server
# Uncomment the block below if you need a second server instance
# if [ -n "$SOVITS_CONFIG_2" ] && [ -n "$SOVITS_PORT_2" ]; then
#     echo "→ Starting GPT-SoVITS server 2 on ${SOVITS_HOST}:${SOVITS_PORT_2}..."
#     bash -c "source ${VENV_SOVITS}/bin/activate && cd ${SOVITS_ROOT} && python3 api_v2.py -a ${SOVITS_HOST} -p ${SOVITS_PORT_2} -c ${SOVITS_CONFIG_2}" &
# fi

echo ""
echo "========================================="
echo "✅ All servers launched successfully"
echo "========================================="
echo ""
echo "Active servers:"
echo "  • Animation server: ${SERVER_DIR}/server.py"
echo "  • Vite client: ${CLIENT_DIR}"
echo "  • GPT-SoVITS: ${SOVITS_HOST}:${SOVITS_PORT}"
echo ""
echo "To stop all servers, run:"
echo "  pkill -f 'python3 api_v2.py|server.py|npx vite'"
echo ""
