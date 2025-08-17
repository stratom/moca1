#!/bin/bash
pm2 start start_streamlit.sh --name frontend
pm2 save
