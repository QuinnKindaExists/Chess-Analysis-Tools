import pygame, pygame.freetype, chess, chess.engine

pygame.init()
screen = pygame.display.set_mode((1280, 720))
clock = pygame.time.Clock()
running = True

board = chess.Board()
font = pygame.freetype.SysFont(None, 32)

def draw():
    font.render_to(screen, (50,50), "Hi")
    pygame.display.flip()

def drawBoardSquare(pos, piece, pieceColor):
    square = pygame.draw.rect()

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill("white")

    clock.tick(60)
    draw()

pygame.quit()