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

Quando a infraestrutura centralizada cai, a população fica isolada exatamente no momento em que mais precisa se comunicar.

## A solução

Uma **rede mesh descentralizada baseada em LoRa** (Long Range), distribuída preventivamente em áreas de risco, que funciona **sem internet, sem rede elétrica e sem torres de celular**.

Cada nó é um dispositivo autônomo composto por um ESP32 com módulo LoRa, alimentado por bateria e painel solar. Os nós se comunicam entre si automaticamente, retransmitindo mensagens e estendendo o alcance por quilômetros. Qualquer pessoa com um celular se conecta ao nó mais próximo via Wi-Fi ou Bluetooth e envia mensagens de texto e localização GPS.

### Nacionalização

Dispositivos LoRa comerciais como Heltec LoRa V3 e LILYGO T-Beam custam entre R$ 150 e R$ 350 no Brasil, são importados e dependem de cadeia logística internacional. Nosso projeto propõe replicar a funcionalidade desses dispositivos usando componentes genéricos (ESP32 + módulo LoRa SX1262 separado + bateria LiPo + painel solar), reduzindo custo e dependência de importação. A versão nacionalizada será demonstrada com hardware já adquirido nas próximas etapas do projeto.

### Conexão com a economia espacial

LoRa é uma tecnologia que já opera no espaço. A **Lacuna Space** (Reino Unido) mantém satélites em órbita baixa equipados com gateways LoRa, permitindo que dispositivos na superfície transmitam dados diretamente para o espaço sem infraestrutura intermediária. Em fevereiro de 2026, essa tecnologia foi aberta para parceiros globais. A mesma rede mesh terrestre que propomos poderia, no futuro, integrar-se com esses satélites para cobertura verdadeiramente global.

## Estrutura da POC

Esta entrega é uma **Prova de Conceito** — não um produto funcional. O objetivo é validar que a tese é viável. A POC se organiza em três camadas:

### 🟢 Camada funcional — código rodando

- **ESP32 simulado no Wokwi**: nó de emergência com monitoramento de bateria (ADC), lógica de estados de energia (normal → economia → crítico → desligamento), display OLED mostrando nome do nó, estado, nível de bateria e status simulado da mesh
- **Python com dados reais**: análise exploratória das enchentes de maio de 2024 usando dados da ANA (nível dos rios Guaíba e Taquari) e INPE (precipitação), com visualizações em Matplotlib e Seaborn
- **Modelo de Machine Learning**: classificação complementar de risco de enchente (baixo/médio/alto/crítico) treinado com dados reais do período

### 🔵 Camada demonstrada — tecnologia que já existe

- **Meshtastic**: firmware open-source para ESP32 + LoRa que implementa comunicação mesh automaticamente. Field tests documentados com alcance de 5 a 15 km. Centenas de milhares de nós ativos no mundo. Referenciado via documentação e cases de uso reais
- **Hardware comercial**: comparação de custo entre dispositivos importados (Heltec V3, T-Beam) e a proposta de nacionalização com componentes genéricos
- **Hardware adquirido**: módulos ESP32 + LoRa comprados, aguardando entrega para testes reais nas próximas etapas

### 🗺️ Plano de implantação — teste local em Ijuí

Três residências em Ijuí-RS foram selecionadas como pontos de teste para a rede mesh. O plano define a localização de cada nó, a distância estimada entre eles e a cobertura esperada. A validação em campo será realizada quando o hardware chegar, com resultados documentados nas próximas entregas.

### 🟣 Camada tese — visão de futuro

- **Integração LoRa-satélite**: protocolo LR-FHSS para uplink direto dispositivo → satélite LEO via Lacuna Space
- **Nós autônomos com energia solar**: bateria LiPo + painel solar + controlador de carga, com gestão inteligente de consumo pelo ESP32
- **Estações meteorológicas integradas**: pluviômetro, sensor de nível e anemômetro acoplados aos nós, transformando cada relay em ponto de coleta ambiental
- **Programa de educação comunitária**: capacitação de líderes comunitários e Defesa Civil para operação da rede em emergências

## Tecnologias utilizadas

| Componente | Tecnologia | Status na POC |
|------------|-----------|---------------|
| Microcontrolador | ESP32 | Simulado (Wokwi) |
| Comunicação | LoRa SX1262 + Meshtastic | Demonstrado (referências) |
| Análise de dados | Python, Pandas, Matplotlib, Seaborn | Funcional |
| Machine Learning | Scikit-learn | Funcional |
| Simulação | Wokwi | Funcional |
| Dados | ANA, INPE, Defesa Civil RS | Dados reais |

## Disciplinas integradas

| Disciplina | Aplicação no projeto |
|-----------|---------------------|
| Computational Thinking | Decomposição em camadas de validação da POC |
| Python & Data Analysis | Análise exploratória com Pandas, visualizações Matplotlib/Seaborn |
| Estatística Aplicada | Correlação precipitação × nível dos rios, métricas do modelo |
| Machine Learning Introdutório | Classificação de risco de enchente |
| IoT & Edge Computing | ESP32 como nó autônomo com lógica de estados |
| Automação & Sensores | Leitura ADC de bateria, controle de display OLED |

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
