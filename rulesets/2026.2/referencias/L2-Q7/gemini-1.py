# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L2-Q7, sem nenhum código de aluno. Revise antes do merge.
hp_noel = 100
dano_breu = 15

total_presentes = 0
total_carvao = 0
custo_global = 0.0

executando = True

while executando:
    nome_local = input()
    if nome_local == "FIM":
        break
    
    continente = input()
    pais = input()
    
    # Fator continente
    if continente == "Europa":
        f_cont = 1.0
    elif continente == "Oceania":
        f_cont = 2.0
    elif continente == "América":
        f_cont = 3.0
    elif continente == "África":
        f_cont = 4.0
    elif continente == "Ásia":
        f_cont = 5.0
    else:
        f_cont = 1.0
        
    # Modificador país
    if pais == "Brasil":
        f_pais = 1.10
    elif pais == "EUA":
        f_pais = 1.15
    elif pais == "China":
        f_pais = 1.20
    elif pais == "Canadá":
        f_pais = 1.25
    elif pais == "Rússia":
        f_pais = 1.30
    else:
        f_pais = 1.00
        
    custo_base_atual = 10.0
    custo_local = 0.0
    sobrecarregado = False
    
    streak_presente = 0
    streak_carvao = 0
    
    while executando:
        evento = input()
        if evento == "FIM_LOCAL":
            break
        
        if evento == "Breu":
            print("Alerta! Breu atacou a entrega!")
            hp_breu = 50
            iniciativa = input()
            turno_noel = (iniciativa == "Noel")
            
            while hp_breu > 0 and hp_noel > 0:
                acao = input()
                if turno_noel:
                    hp_breu -= 20
                else:
                    hp_noel -= dano_breu
                turno_noel = not turno_noel
                
            if hp_noel <= 0:
                print("O HP de Noel chegou a zero! O Breu venceu a batalha... O Natal das crianças foi arruinado.")
                executando = False
                break
            else:
                print("Noel repeliu a emboscada e as entregas continuam!")
        else:
            # Fluxo de entrega
            while True:
                pontuacao_str = input()
                pontuacao = int(pontuacao_str)
                if 0 <= pontuacao <= 100:
                    break
                print("Pontuação inválida, insira novamente.")
                
            custo_crianca = custo_base_atual * f_cont * f_pais
            custo_local += custo_crianca
            custo_global += custo_crianca
            
            if custo_local > 100.0 and not sobrecarregado:
                print("O trenó está sobrecarregado pela magia! Custos base aumentados.")
                sobrecarregado = True
                custo_base_atual = 15.0
                
            if pontuacao >= 70:
                print(f"{evento} foi uma boa criança este ano e receberá um presente!")
                total_presentes += 1
                streak_presente += 1
                streak_carvao = 0
                if streak_presente == 3:
                    print("A fé das crianças fortalece a magia! Noel recuperou 10 de HP.")
                    hp_noel += 10
                    if hp_noel > 100:
                        hp_noel = 100
                    streak_presente = 0
            else:
                print(f"{evento} não se comportou bem e receberá carvão.")
                total_carvao += 1
                streak_carvao += 1
                streak_presente = 0
                if streak_carvao == 3:
                    dano_breu += 5
                    print(f"O medo e a descrença alimentam as sombras... O dano de Breu aumentou para {dano_breu}!")
                    streak_carvao = 0

    if executando:
        print(f"Localidade {nome_local} finalizada. Custo logístico: {custo_local:.2f}")

if hp_noel > 0:
    print(f"Noite concluída com sucesso! Presentes: {total_presentes} | Carvão: {total_carvao}")
    print(f"Custo logístico total: {custo_global:.2f}")
    print(f"HP final do Noel: {hp_noel}")
