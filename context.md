# context.md — Referência técnica para Claude Code

## Projeto

POC acadêmica — rede LoRa mesh para comunicação de emergência.
Case: enchentes RS 2024. Entrega: GS 2026.1 FIAP. Prazo: 1 semana.

## 3 camadas da POC

| Camada | Conteúdo |
|--------|----------|
| Funcional | ESP32 Wokwi (energia do nó) + Python dados RS + ML risco |
| Demonstrada | Meshtastic existe e funciona (refs) + hardware comercial (comparação custo) + hardware comprado (a caminho) |
| Tese | Satélite (Lacuna Space) + energia solar + estações meteo + nacionalização com ESP32 + educação comunitária |

O mapa com 3 nós em Ijuí é plano de implantação, não teste realizado.
Hardware LoRa comprado, ainda não chegou. Demo real na próxima entrega.

## Stack

- ESP32: Arduino/C++ (simulado Wokwi)
- Python 3.10+: pandas, numpy, matplotlib, seaborn, scikit-learn
- Testes: pytest
- Dados: CSV (ANA, INPE — recorte maio/2024, 2-4 semanas, 1-2 rios)

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

- Testes junto com implementação
- 1 feature = 1 commit funcional
- Nunca commitar direto — humano revisa
- Código duplicou → extrair. Arquivo > 200 linhas → dividir

## ESP32 — Firmware do nó

### Função
Gestão de energia: lê bateria, classifica estado, exibe no OLED.
Prova que o nó sabe sobreviver sozinho.

### Pinos

| Pino | Componente Wokwi | Componente real |
|------|-------------------|-----------------|
| GPIO 34 | Potenciômetro | Divisor resistivo bateria |
| GPIO 35 | Push button | TP4056 STDBY |
| GPIO 21 | OLED SDA | OLED SDA |
| GPIO 22 | OLED SCL | OLED SCL |
| GPIO 2 | LED onboard | LED onboard |

### Thresholds bateria

| Tensão | Estado | Ação |
|--------|--------|------|
| ≥ 3.70V | NORMAL | Operação padrão |
| 3.40–3.70V | ECONOMIA | Reduz frequência display |
| 3.20–3.40V | CRITICO | LED pisca, alerta OLED |
| < 3.20V | DESLIGAMENTO | Mensagem final, desliga |

### Conversão ADC
Divisor 100k/100k: `tensao = (adc_raw / 4095.0) * 3.3 * 2.0`

### OLED — layout do display
Mostrar contexto de nó de emergência, não apenas número de bateria:
- Linha 1: nome do nó (ex: "LORA-RS-001")
- Linha 2: estado (NORMAL / ECONOMIA / CRITICO)
- Linha 3: barra visual de bateria + percentual
- Linha 4: ícone antena + "MESH OK" ou "MESH OFF" (simulado)

### Libs Arduino
- Adafruit SSD1306, Adafruit GFX, Wire

## Python — Análise

### analise_enchente_rs.py
Entrada: CSVs em data/
Saída: gráficos PNG + estatísticas

Gráficos:
1. Nível do rio vs tempo (linha de alerta + inundação marcadas)
2. Precipitação acumulada por período
3. Scatter precipitação × nível (correlação)

### modelo_preditivo.py
Modelo: classificação risco (baixo/médio/alto/crítico)
Features: precipitação acumulada (24h, 48h, 72h), nível atual, taxa de subida
Target: classe derivada dos thresholds ANA
Algoritmo: DecisionTree ou RandomForest
Métricas: acurácia, F1-score, matriz confusão
ML é complementar, não core. Mantê-lo simples e funcional.

### Testes (pytest)
- test_analise.py: carga dados, limpeza, cálculos
- test_modelo.py: features, split, treino, predição

### Convenções
- Funções com docstrings, snake_case
- Um script = uma responsabilidade
- Sem Jupyter — só .py

## Dados

Recorte mínimo: maio/2024, 2-4 semanas, 1-2 rios (Guaíba + Taquari).

niveis_rios_rs.csv:
```
data_hora,estacao,rio,nivel_cm,nivel_alerta_cm,nivel_inundacao_cm
```

precipitacao_rs.csv:
```
data,estacao,municipio,precipitacao_mm
```

Fontes: ANA HidroWeb, INPE BDMEP.
Se dados reais difíceis de obter: criar CSV com valores oficiais documentados.

## Hurdles

| ID | Problema | Solução |
|----|---------|---------|
| H1 | LoRa não existe no Wokwi | Simular só energia. LoRa = camada demonstrada |
| H2 | Dados ANA formato ruim | Pré-processar + testar. Ou criar CSV realista |
| H3 | Potenciômetro Wokwi 0-3.3V | Multiplicar por 2 no código |
| H4 | Hardware LoRa não chegou | Demo real na próxima entrega |

## Prompt para Claude Code

```
Leia o context.md antes de qualquer coisa.
[descrever a feature]
Implemente com testes.
Não faça commit — eu vou revisar.
```
