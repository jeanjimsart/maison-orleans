#!/usr/bin/env bash
# Chaîne complète : collecte -> notation -> photos -> données de la page
cd "$(dirname "$0")"
python3 collect_bienici.py && python3 collect_notaires.py && python3 merge_alertes.py && python3 dvf.py >/dev/null && python3 score.py && python3 photos.py && python3 site_data.py
