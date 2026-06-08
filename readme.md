<p align="center">
  <img src="../../assets/logo-fiap.png" alt="FIAP" width="300">
</p>

# 🛰️ LoRa Emergência RS

### Rede de comunicação de emergência para desastres climáticos

**Global Solution 2026.1 — Economia Espacial**

---

## O problema

Em maio de 2024, o Rio Grande do Sul viveu a maior catástrofe climática da sua história.

| Impacto | Número |
|---------|--------|
| Mortos | 181 |
| Desaparecidos | 61 |
| Pessoas em abrigos | 75.000+ |
| Municípios afetados | 478 de 497 |
| Dano estimado | R$ 19 bilhões |

Um dos fatores que agravou a tragédia foi o **colapso das redes de comunicação**. Estudo da UFRGS documentou que, na fase mais crítica, até 25% das estações rádio base estavam offline em Porto Alegre. As redes que sobreviveram foram as obsoletas 2G/3G — em processo de desativação — sustentando apenas SMS e WhatsApp em modo precário.

Quando a infraestrutura centralizada cai, a população fica isolada exatamente no momento em que mais precisa de comunicação. Resgates atrasam. Famílias perdem contato. Pessoas morrem sem pedir ajuda.

## A solução

Uma **rede mesh descentralizada baseada em LoRa** (Long Range), distribuída preventivamente em áreas de risco, que funciona **sem internet, sem rede elétrica e sem torres de celular**.

Cada nó da rede é um dispositivo autônomo composto por um ESP32 com módulo LoRa, alimentado por bateria e painel solar. Os nós se comunicam entre si automaticamente, retransmitindo mensagens e estendendo o alcance da rede por quilômetros. Qualquer pessoa com um celular pode se conectar ao nó mais próximo via Wi-Fi ou Bluetooth e enviar mensagens de texto e localização GPS.

**Quando as torres caem, a mesh sobrevive.**

## Por que isso é economia espacial?

LoRa não é apenas uma tecnologia terrestre — é uma tecnologia que já opera no espaço.

A **Lacuna Space** (Reino Unido) mantém uma constelação de satélites em órbita baixa equipados com gateways LoRa. Desde 2019, dispositivos LoRa na superfície terrestre transmitem dados diretamente para esses satélites, sem necessidade de infraestrutura intermediária. Em fevereiro de 2026, no Mobile World Congress, a Lacuna Space abriu essa tecnologia para parceiros globais.

Isso significa que a mesma rede mesh terrestre que propomos poderia, no futuro, ser estendida via satélite para cobertura verdadeiramente global. O mesmo protocolo. O mesmo hardware. Alcance planetário.

## Estrutura da POC

Esta entrega é uma **Prova de Conceito** organizada em três camadas de validação:

### 🟢 Funcional — o que roda ao vivo

- **ESP32 no Wokwi**: simulação do nó de emergência com monitoramento de bateria (ADC), lógica de estados de energia (normal → economia → crítico → desligamento) e display OLED mostrando status em tempo real
- **Python com dados reais**: análise exploratória das enchentes do RS usando dados da ANA (nível dos rios) e INPE (precipitação), com visualizações em Matplotlib e Seaborn
- **Modelo de Machine Learning**: classificação de risco de enchente (baixo / médio / alto / crítico) treinado com dados reais, avaliado com métricas de acurácia e F1-score

### 🔵 Demonstrada — tecnologia que já existe

- **Meshtastic**: firmware open-source para ESP32 + LoRa SX1262 que implementa comunicação mesh automaticamente. Field tests documentados com alcance de 5 a 15 km em campo aberto. Centenas de milhares de nós ativos no mundo.
- **Hardware adquirido** (em trânsito): módulos ESP32 + LoRa para testes reais em campo, demonstração futura fora do escopo desta entrega.

### 🟣 Tese — a visão do sistema completo

- **Integração LoRa-satélite**: protocolo LR-FHSS para uplink direto dispositivo → satélite LEO (Lacuna Space)
- **Nós autônomos com energia solar**: bateria LiPo + painel solar + controlador de carga TP4056, com gestão inteligente de consumo pelo ESP32
- **Estações meteorológicas integradas**: pluviômetro, sensor de nível, anemômetro acoplados aos nós, transformando cada relay em ponto de coleta ambiental que alimenta o modelo preditivo em tempo real
- **Programa de educação comunitária**: capacitação de líderes comunitários e agentes de Defesa Civil para operação e manutenção da rede

## Tecnologias utilizadas

| Componente | Tecnologia | Status |
|------------|-----------|--------|
| Microcontrolador | ESP32 | Simulado (Wokwi) |
| Comunicação | LoRa SX1262 + Meshtastic | Demonstrado |
| Análise de dados | Python, Pandas, Matplotlib, Seaborn | Funcional |
| Machine Learning | Scikit-learn | Funcional |
| Simulação | Wokwi | Funcional |
| Dados | ANA, INPE, Defesa Civil RS | Dados reais |

## Disciplinas integradas

| Disciplina | Aplicação no projeto |
|-----------|---------------------|
| Computational Thinking | Decomposição do problema em 3 camadas de validação |
| Python & Data Analysis | Análise exploratória com Pandas, visualizações com Matplotlib/Seaborn |
| Estatística Aplicada | Correlação chuva × nível dos rios, métricas do modelo preditivo |
| Machine Learning Introdutório | Classificação de risco de enchente com dados reais |
| IoT & Edge Computing | ESP32 como nó autônomo com lógica de estados |
| Automação & Sensores | Leitura ADC de bateria, controle de display OLED, gestão de energia |

## Como executar

### Python

```bash
cd 1TIAO/global-solution/src/python
pip install -r requirements.txt
python analise_enchente_rs.py
python modelo_preditivo.py
pytest tests/
```

### ESP32 (Wokwi)

1. Acessar [wokwi.com](https://wokwi.com)
2. Importar `wokwi/diagram.json`
3. Colar código de `src/esp32/lora_node_energy.ino`
4. Iniciar simulação

## Estrutura do repositório

```
1TIAO/global-solution/
├── src/
│   ├── esp32/              ← Firmware do nó (gestão de energia)
│   └── python/             ← Análise de dados + ML + testes
├── docs/                   ← Justificativa espacial e diagramas
├── data/                   ← Datasets reais (ANA, INPE)
├── wokwi/                  ← Simulação do circuito
└── README.md               ← Este arquivo
```

## Referências

- UFRGS / NIC.br (2025). *Resiliência de rede 2G em enchentes no RS*. 40º GTS.
- Lacuna Space (2026). *LoneWhisper® D2D*. Mobile World Congress.
- LoRa Alliance (2025). *Extending LoRaWAN to Satellite Networks*. White Paper.
- Meshtastic Project. https://meshtastic.org
- Governo do RS. *SOS Enchentes*. https://sosenchentes.rs.gov.br
- ANA. *HidroWeb*. https://www.snirh.gov.br/hidroweb
- INPE. *BDMEP*. https://bdmep.inmet.gov.br

## 🎥 Vídeo demonstrativo

📹 [Link YouTube — Não Listado]

## 👥 Integrantes

| Nome | RM |
|------|-----|
| [Nome 1] | RMXXXXX |
| [Nome 2] | RMXXXXX |
| [Nome 3] | RMXXXXX |
| [Nome 4] | RMXXXXX |
| [Nome 5] | RMXXXXX |