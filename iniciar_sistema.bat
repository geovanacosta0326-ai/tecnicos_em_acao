@echo off
title Atualizacao Automatica CIIAGRO
color 0A

echo ========================================
echo EXECUTANDO api_sisateg
echo ========================================
python "C:\Users\geovana\api_sisateg.py"

echo ========================================
echo EXECUTANDO api_visitas
echo ========================================
python "C:\Users\geovana\api_visitas.py"

echo ========================================
echo EXECUTANDO sincronizarblocal_bservidor
echo ========================================
python "C:\CIIAGRO2\Dados Georrefrenciados\tecnicos_em_acao\sincronizarblocal_bservidor.py"

echo ========================================
echo PROCESSO FINALIZADO
echo ========================================

pause