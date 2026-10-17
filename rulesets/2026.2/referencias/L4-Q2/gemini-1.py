# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L4-Q2, sem nenhum código de aluno. Revise antes do merge.
HP_MAX = {
    "Cavaleiro": 55,
    "Paladino": 80,
    "Sacerdotisa": 60,
    "Necromante": 40,
    "Assassino": 45,
    "Bruxa": 50
}

def selecionar_personagem(nome):
    return nome, HP_MAX[nome]

def aplicar_efeito_sala(personagem, hp_atual, sala):
    max_hp = HP_MAX[personagem]
    if sala == '+':
        hp_atual += 20
        if hp_atual > max_hp:
            hp_atual = max_hp
    elif sala == 'c':
        hp_atual -= 15
    elif sala == '@':
        hp_atual -= 25
    return hp_atual

def movimentar(matriz, direcoes, personagem, hp_atual):
    r, c = 0, 0
    passos = 0
    
    for dir_ in direcoes:
        nr, nc = r, c
        if dir_ == '>':
            nc += 1
        elif dir_ == '<':
            nc -= 1
        elif dir_ == 'v':
            nr += 1
        elif dir_ == '^':
            nr -= 1
            
        if 0 <= nr < 5 and 0 <= nc < 5:
            r, c = nr, nc
            passos += 1
            sala = matriz[r][c]
            hp_atual = aplicar_efeito_sala(personagem, hp_atual, sala)
            
            if sala == 'c':
                print(f"O(A) {personagem} prevalece no combate, mantendo-se firme com {hp_atual} HP!")
            
            if hp_atual <= 0:
                return False, hp_atual, passos, r, c
                
            if r == 4 and c == 4:
                if hp_atual > 0:
                    return True, hp_atual, passos, r, c
                else:
                    return False, hp_atual, passos, r, c
                    
    return None, hp_atual, passos, r, c

def transposta(matriz):
    return [[matriz[j][i] for j in range(5)] for i in range(5)]

def executar_tentativa(personagem, matriz, direcoes):
    p_nome, hp = selecionar_personagem(personagem)
    print(f"O(A) {p_nome} é o(a) herói(na) lendário(a) escolhido(a)!")
    
    # A00 não causa dano inicial, apenas efeito se houver (mas A00 é garantidamente '.')
    sucesso, hp_final, passos, r, c = movimentar(matriz, direcoes, p_nome, hp)
    
    if sucesso:
        print("A profecia se cumpriu e a paz reina mais uma vez!")
        print(f"Cruzando as profundezas da masmorra em {passos} passos de pura bravura, o(a) nosso(a) herói(na) ergue-se triunfante com {hp_final} HP.")
        return True
    else:
        return False

def main():
    print("A jornada pela Pedra Mágica tem início! O destino do reino está selado, e esta guerra finalmente encontrará o seu fim.")
    print()
    
    p1 = input().strip()
    matriz1 = [input().split() for _ in range(5)]
    direcoes1 = input().strip()
    
    if executar_tentativa(p1, matriz1, direcoes1):
        return
        
    print("Ainda não é o fim! A jornada continua…")
    print()
    
    p2 = input().strip()
    direcoes2 = input().strip()
    matriz2 = transposta(matriz1)
    
    if executar_tentativa(p2, matriz2, direcoes2):
        return
        
    print("Sem heróis. Sem esperança. O Reino caiu.")

if __name__ == '__main__':
    main()
