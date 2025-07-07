#Fotovoltaico.py

Simulador 3D de Fazenda Fotovoltaica com Sombreamento e Geração de Energia

## Descrição
Este script implementa uma simulação 3D interativa de uma fazenda de painéis solares, utilizando OpenGL e Pygame. O sistema permite visualizar painéis solares, ajustar o horário do dia, o tipo e a quantidade de painéis, e exibe em tempo real a geração total de energia considerando a posição do sol e a inclinação dos painéis. O código também implementa sombras realistas via shadow mapping.

## Funcionalidades
- Visualização 3D de painéis solares, terreno e postes de suporte
- Cálculo dinâmico da geração de energia dos painéis baseado na posição do sol
- Sombreamento realista dos objetos (shadow mapping)
- HUD com informações de geração total (kW) e número de painéis
- Controle de câmera em primeira pessoa (WASD + mouse)
- Ajuste do horário do dia e seleção do tipo de painel
- Aumento/diminuição do número de colunas de painéis

## Controles
- **W, A, S, D**: Mover a câmera
- **Mouse**: Girar a câmera
- **ESC**: Sair
- **Seta para cima/baixo**: Avançar/retroceder o horário do sol
- **1, 2, 3**: Selecionar tipo de painel (160W, 330W, 610W)
- **+ / -**: Aumentar/diminuir o número de colunas de painéis

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
- O HUD é desenhado sobre a cena 3D usando pygame.freetype.

## Autor
Desenvolvido por Vitor 
