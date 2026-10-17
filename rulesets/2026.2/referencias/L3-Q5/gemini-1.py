# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L3-Q5, sem nenhum código de aluno. Revise antes do merge.
linhas = int(input())
colunas = int(input())

if linhas <= 0 or colunas <= 0:
    print("Dimensões do mapa inválidas!")
else:
    matriz = []
    for i in range(linhas):
        linha = []
        for j in range(colunas):
            valor = int(input())
            linha.append(valor)
        matriz.append(linha)
    
    aliado = input()
    limite_energia = int(input())
    
    # Processamento da matriz
    for i in range(linhas):
        for j in range(colunas):
            val = matriz[i][j]
            
            # Diagonal principal
            is_dp = (i == j)
            # Diagonal secundária (matriz quadrada e i + j == linhas - 1)
            is_ds = (linhas == colunas and (i + j == linhas - 1))
            
            if is_dp and is_ds:
                val = val * 2
                val = val + 5
            elif is_dp:
                val = val * 2
            elif is_ds:
                val = val + 5
                
            # Filtro de Segurança
            if val < 15:
                val = 0
            
            # Estabilidade de Dobra
            if val % 2 != 0:
                val = val + 1
                
            matriz[i][j] = val

    print("Avatar: A Lenda de Aang - Planejamento da Invasão!")
    print("Sokka: Mapeando os setores da Nação do Fogo...")
    
    for i in range(linhas):
        linha_str = ""
        for j in range(colunas):
            if j == 0:
                linha_str = str(matriz[i][j])
            else:
                linha_str = linha_str + " " + str(matriz[i][j])
        print(linha_str)
        
    # Relatório
    soma_total = 0
    maior_valor = -1
    critico_linha = 0
    critico_coluna = 0
    
    pares = 0
    impares = 0
    
    for i in range(linhas):
        for j in range(colunas):
            v = matriz[i][j]
            soma_total = soma_total + v
            
            if v % 2 == 0:
                pares = pares + 1
            else:
                impares = impares + 1
                
            if i == 0 and j == 0:
                maior_valor = v
                critico_linha = i
                critico_coluna = j
            else:
                if v > maior_valor:
                    maior_valor = v
                    critico_linha = i
                    critico_coluna = j
                    
    print("--- RELATÓRIO DO TÚNEL E AMEAÇAS ---")
    print("Soma Total de Resistência:", soma_total)
    print("Setor Mais Crítico: (" + str(critico_linha) + ", " + str(critico_coluna) + ") com valor " + str(maior_valor))
    
    # Cenário estratégico
    if soma_total < 100:
        print("Sokka: O mapa revela poucas defesas inimigas!")
        print("Aang: Parece que o caminho está livre.")
        print("Katara: Conseguimos passar sem grandes problemas!")
        print("Estratégia aprovada! O Avatar está pronto para a batalha.")
    elif soma_total < 200:
        print("Sokka: Atenção! Detectamos resistência nas defesas da Nação do Fogo.")
        print("Toph: Sinto muitas tropas pelo solo, mas podemos avançar com cuidado.")
        print("Aang: Então vamos atentos. A Equipe Avatar está pronta!")
        print("Estratégia aprovada, mas a invasão será realizada com cautela.")
    else:
        print("Sokka: Alerta! As defesas inimigas são muito fortes!")
        print("Toph: A linha de defesa deles é densa demais para atravessarmos.")
        print("Aang: Então precisamos recuar e repensar nosso plano.")
        print("Alerta vermelho: Nível de ameaça crítico! Invasão adiada.")
        
    # Missão dos aliados
    sucesso = False
    if aliado == "Aang":
        if soma_total <= limite_energia:
            sucesso = True
    elif aliado == "Katara":
        if pares > impares:
            sucesso = True
    elif aliado == "Toph":
        if maior_valor <= 50:
            sucesso = True
    elif aliado == "Sokka":
        if linhas == colunas:
            sucesso = True
            
    if sucesso:
        print(aliado + " usou sua especialidade com maestria e garantiu o sucesso na missão!")
    else:
        print(aliado + " encontrou barreiras intransponíveis e a missão precisou ser abortada...")
