# Fotovoltaico.py

Simulador 3D de Fazenda Solar Fotovoltaica com Sombreamento, Geração e Bateria

## Descrição
Este script simula uma fazenda solar 3D interativa, utilizando Python, Pygame e OpenGL moderno (shaders). O sistema permite visualizar painéis solares, ajustar o horário do dia, o tipo e a quantidade de painéis, inclinação e azimute dos painéis, além de exibir em tempo real a geração de energia e o carregamento de uma bateria virtual. O código implementa sombras realistas via shadow mapping e um HUD informativo.

## Funcionalidades
- Visualização 3D de painéis solares, terreno, postes, gabinete de bateria e placa digital de geração
- Cálculo dinâmico da geração de energia dos painéis baseado na posição do sol, inclinação e azimute
- Simulação de carregamento de bateria (capacidade, status, porcentagem)
- Sombreamento realista dos objetos (shadow mapping)
- HUD com informações de geração, número de painéis, status e carga da bateria
- Controle de câmera em primeira pessoa (WASD + mouse)
- Ajuste do horário do dia, tipo, quantidade, inclinação e azimute dos painéis
- Placa digital 3D mostrando a geração em tempo real

## Controles
- **W, A, S, D**: Mover a câmera
- **Mouse**: Girar a câmera
- **ESC**: Sair
- **Seta para cima/baixo**: Avançar/retroceder o horário do sol
- **1, 2, 3**: Selecionar tipo de painel (160W, 330W, 610W)
- **+ / -**: Aumentar/diminuir o número de colunas de painéis
- **Q / E**: Girar o azimute dos painéis (orientação horizontal)

## Requisitos
- Python 3.8+
- Pygame
- PyOpenGL
- Pillow (PIL)
- numpy

Instale as dependências com:
```bash
pip install pygame PyOpenGL Pillow numpy
```

## Texturas Necessárias
Coloque os arquivos de textura na mesma pasta do script:
- `grass.png` (grama)
- `solar_cell.png` (célula solar)
- `metal_frame.png` (estrutura metálica)

## Execução
Execute o script com:
```bash
python Fotovoltaico.py
```

## Observações
- O cálculo de geração de energia é simplificado e serve para fins didáticos.
- O código utiliza OpenGL moderno (shaders) e shadow mapping para sombras.
- O HUD mostra geração, número de painéis, status e carga da bateria.
- A placa digital 3D exibe a geração em tempo real.

## Autor
Desenvolvido por Vitor (2025)
