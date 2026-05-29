# context.md — Guia técnico para Claude Code

## O que é este projeto

POC acadêmica. Rede LoRa mesh para emergências. Enchentes RS 2024.
Entrega em 1 semana. Código precisa rodar e ter testes.

## Stack

- ESP32: Arduino/C++ (simulado no Wokwi)
- Python 3.10+: pandas, numpy, matplotlib, seaborn, scikit-learn
- Testes Python: pytest
- Dados: CSV (ANA, INPE)

## Estrutura de arquivos

```
1TIAO/global-solution/
├── src/
│   ├── esp32/
│   │   ├── lora_node_energy.ino
│   │   └── config.h
│   └── python/
│       ├── analise_enchente_rs.py
│       ├── modelo_preditivo.py
│       ├── tests/
│       │   ├── test_analise.py
│       │   └── test_modelo.py
│       └── requirements.txt
├── data/
│   └── *.csv
└── wokwi/
    └── diagram.json
```

## Regras de desenvolvimento

- Testes junto com implementação. Nunca depois.
- 1 feature = 1 commit. Cada commit funciona sozinho.
- Nunca commitar direto. Eu reviso antes.
- Se duplicou código, extrair. Se passou 200 linhas, dividir.

## ESP32 — Firmware do nó

### O que faz
Gerencia energia de um nó LoRa. Lê bateria, classifica estado, exibe no OLED.

### Pinos

| Pino | Componente | Função |
|------|-----------|--------|
| GPIO 34 | Potenciômetro (Wokwi) / Divisor resistivo (real) | ADC bateria |
| GPIO 35 | Push button (Wokwi) / TP4056 STDBY (real) | Carga solar ativa |
| GPIO 21 | OLED SDA | Display I2C |
| GPIO 22 | OLED SCL | Display I2C |
| GPIO 2 | LED onboard | Status visual |

### Thresholds de bateria

| Tensão | % | Estado | Ação |
|--------|---|--------|------|
| ≥ 3.70V | > 50% | NORMAL | Operação padrão |
| 3.40–3.70V | 20–50% | ECONOMIA | Reduz frequência de display |
| 3.20–3.40V | 10–20% | CRITICO | LED pisca, alerta no OLED |
| < 3.20V | < 10% | DESLIGAMENTO | Mensagem final, desliga |

### Conversão ADC → tensão
Divisor resistivo 100k/100k: Vout = Vin / 2.
ADC 12-bit (0–4095), referência 3.3V.
`tensao_bateria = (adc_raw / 4095.0) * 3.3 * 2.0`

### Wokwi
- Potenciômetro no pino 34 simula tensão da bateria (girar = mudar carga)
- Push button no pino 35 simula carga solar (pressionado = carregando)
- OLED I2C SSD1306 128x64 nos pinos 21/22
- Sem módulo LoRa (não existe no Wokwi)

### Libs Arduino necessárias
- Adafruit SSD1306
- Adafruit GFX
- Wire (built-in)

## Python — Análise de dados

### analise_enchente_rs.py
Entrada: CSVs em data/ (nível rios, precipitação)
Saída: gráficos salvos em PNG + prints de estatísticas descritivas

Gráficos obrigatórios:
1. Nível do rio vs tempo (destacar nível de alerta e inundação)
2. Precipitação acumulada por período
3. Correlação precipitação × nível do rio (scatter + regressão)

Libs: pandas, matplotlib, seaborn

### modelo_preditivo.py
Entrada: mesmo CSV processado
Saída: métricas do modelo + gráficos de avaliação

Modelo: classificação de risco (baixo/médio/alto/crítico)
Features: precipitação acumulada (24h, 48h, 72h), nível atual, taxa de subida
Target: classe de risco (derivada dos thresholds oficiais ANA)
Algoritmo: começar com DecisionTree ou RandomForest (simples, interpretável)
Métricas: acurácia, F1-score, matriz de confusão

Libs: pandas, scikit-learn, matplotlib

### Testes (pytest)
- test_analise.py: testa carga de dados, limpeza, cálculos de correlação
- test_modelo.py: testa feature engineering, split, treino, predição

### Convenções Python
- Funções com docstrings
- Nomes em snake_case
- Um script = uma responsabilidade
- Sem notebooks Jupyter (só .py)

## Dados

### Formato esperado dos CSVs

niveis_rios_rs.csv:
```
data_hora,estacao,rio,nivel_cm,nivel_alerta_cm,nivel_inundacao_cm
```

precipitacao_rs.csv:
```
data,estacao,municipio,latitude,longitude,precipitacao_mm
```

### Fontes
- ANA HidroWeb: https://www.snirh.gov.br/hidroweb
- INPE BDMEP: https://bdmep.inmet.gov.br
- Se dados reais não forem obtidos a tempo, criar CSV realista baseado
  nos valores documentados oficialmente. Citar fonte.

## Hurdles conhecidos

| ID | Problema | Solução |
|----|---------|---------|
| H1 | LoRa SX1262 não existe no Wokwi | Simular só gestão de energia |
| H2 | Dados ANA formato inconsistente | Pré-processar + testar integridade |
| H3 | Wokwi potenciômetro range 0–3.3V | Multiplicar por 2 no código (divisor) |