# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L4-Q2, sem nenhum código de aluno. Revise antes do merge.
def selecionar_personagem(nome):
    hps = {
        "Cavaleiro": 55,
        "Paladino": 80,
        "Sacerdotisa": 60,
        "Necromante": 40,
        "Assassino": 45,
        "Bruxa": 50
    }
    return nome, hps[nome]

def aplicar_efeito_sala(sala, hp_atual, hp_max, personagem):
    vivo = True
    if sala == '+':
        hp_atual += 20
        if hp_atual > hp_max:
            hp_atual = hp_max
    elif sala == 'c':
        hp_atual -= 15
        if hp_atual <= 0:
            hp_atual = 0
            vivo = False
        else:
            print(f"O(A) {personagem} prevalece no combate, mantendo-se firme com {hp_atual} HP!")
    elif sala == '@':
        hp_atual -= 25
        if hp_atual <= 0:
            hp_atual = 0
            vivo = False
    return hp_atual, vivo

def movimentar(matriz, direcoes, personagem, hp_atual, hp_max):
    r, c = 0, 0
    passos = 0
    
    for dir_ in direcoes:
        novo_r, novo_c = r, c
        if dir_ == '>':
            novo_c += 1
        elif dir_ == '<':
            novo_c -= 1
        elif dir_ == 'v':
            novo_r += 1
        elif dir_ == '^':
            novo_r -= 1
            
        if 0 <= novo_r < 5 and 0 <= novo_c < 5:
            r, c = novo_r, novo_c
            passos += 1
            sala = matriz[r][c]
            hp_atual, vivo = aplicar_efeito_sala(sala, hp_atual, hp_max, personagem)
            
            if not vivo:
                return False, hp_atual, passos, r, c
            if sala == '@':
                return True, hp_atual, passos, r, c
                
    return None, hp_atual, passos, r, c

def transpor_matriz(matriz):
    return [[matriz[j][i] for j in range(5)] for i in range(5)]

def main():
    print("A jornada pela Pedra Mágica tem início! O destino do reino está selado, e esta guerra finalmente encontrará o seu fim.\n")
    
    p1_nome = input().strip()
    matriz = [input().split() for _ in range(5)]
    direcoes1 = input().strip()
    
    p1, hp_max1 = selecionar_personagem(p1_nome)
    print(f"O(A) {p1} é o(a) herói(na) lendário(a) escolhido(a)!")
    
    venceu, hp_atual, passos, r, c = movimentar(matriz, direcoes1, p1, hp_max1, hp_max1)
    
    if venceu is True:
        print("A profecia se cumpriu e a paz reina mais uma vez!")
        print(f"\nCruzando as profundezas da masmorra em {passos} passos de pura bravura, o(a) nosso(a) herói(na) ergue-se triunfante com {hp_atual} HP.")
        return
    
    if venceu is False or (matriz[r][c] != '@' and hp_atual <= 0):
        print("Ainda não é o fim! A jornada continua…\n")
        p2_nome = input().strip()
        direcoes2 = input().strip()
        
        p2, hp_max2 = selecionar_personagem(p2_nome)
        print(f"O(A) {p2} é o(a) herói(na) lendário(a) escolhido(a)!")
        
        matriz_transposta = transpor_matriz(matriz)
        venceu2, hp_atual2, passos2, _, _ = movimentar(matriz_transposta, direcoes2, p2, hp_max2, hp_max2)
        
        if venceu2 is True:
            print("A profecia se cumpriu e a paz reina mais uma vez!")
            print(f"\nCruzando as profundezas da masmorra em {passos2} passos de pura bravura, o(a) nosso(a) herói(na) ergue-se triunfante com {hp_atual2} HP.")
        else:
            print("Sem heróis. Sem esperança. O Reino caiu.")

if __name__ == '__main__':
    main()
