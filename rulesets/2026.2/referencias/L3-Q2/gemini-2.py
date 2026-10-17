# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L3-Q2, sem nenhum código de aluno. Revise antes do merge.
kit = ["taco_beisebol", "besta", "kit_medico", "feijao_enlatado", "walkie_talkie", "garrafa_agua", "biscoito"]

kit_rick = ["colt_357", "distintivo", "radio_comunicador", "cantil", "curativo"]
kit_michonne = ["katana", "amolador", "binoculo", "faixa_curativo", "mapa"]
kit_daryl = ["arco e flecha", "flechas", "faca_de_caca", "corda", "carne_seca"]
kit_carol = ["facao", "bomba_de_fumaca", "sangue_zumbi", "fosforos", "biscoito"]

sobrevivente = input().strip()

if sobrevivente == "Rick":
    print("Um grande líder sempre ajuda sua equipe, Rick lhe dá uma lanterna para a noite")
    kit.append("lanterna")
    
    # Primeiro Dia
    if "taco_beisebol" in kit:
        kit.remove("taco_beisebol")
    print(f"Kit atual sobrevivente: {kit}")
    
    # Segundo Dia
    itens_dados = kit[2:]
    kit = kit[:2]
    kit_rick.extend(itens_dados)
    print("Agora com as costas mais leves, podemos continuar com a nossa caminhada")
    
    # Terceiro Dia
    print("\nFinalmente chegamos em Alexandria!")
    print(f"\nUfa, podemos ficar aqui por um tempo,{sobrevivente}\n")
    print(f"Kit do sobrevivente: {kit}\nKit do {sobrevivente}: {kit_rick}")

elif sobrevivente == "Michonne":
    print("Michonne é uma ótima combatente, ela te dá uma arma para você não passar apertos.")
    kit.append("faca_afiada")
    
    # Primeiro Dia
    if "kit_medico" in kit:
        kit.remove("kit_medico")
        print("Você usou o kit médico para socorrer Michonne!")
    print(f"Kit atual sobrevivente: {kit}")
    
    # Segundo Dia
    itens_dados = kit[2:]
    kit = kit[:2]
    kit_michonne.extend(itens_dados)
    print("Agora com as costas mais leves, podemos continuar com a nossa caminhada")
    
    # Terceiro Dia
    print("\nFinalmente chegamos em Alexandria!")
    print(f"\nUfa, podemos ficar aqui por um tempo,{sobrevivente}\n")
    print(f"Kit do sobrevivente: {kit}\nKit do {sobrevivente}: {kit_michonne}")

elif sobrevivente == "Daryl":
    print("Daryl é um ótimo caçador. Ele te dá carne para comer na refeição")
    kit.append("carne")
    
    # Primeiro Dia
    if "besta" in kit and "arco e flecha" in kit_daryl:
        idx_besta = kit.index("besta")
        idx_arco = kit_daryl.index("arco e flecha")
        kit[idx_besta] = "arco e flecha"
        kit_daryl[idx_arco] = "besta"
    
    print(f"   Kit atual sobrevivente: {kit}")
    print(f"   Kit atual Daryl: {kit_daryl}")
    
    # Segundo Dia
    itens_dados = kit[2:]
    kit = kit[:2]
    kit_daryl.extend(itens_dados)
    print("Agora com as costas mais leves, podemos continuar com a nossa caminhada")
    
    # Terceiro Dia
    print("\nFinalmente chegamos em Alexandria!")
    print(f"\nUfa, podemos ficar aqui por um tempo,{sobrevivente}\n")
    print(f"Kit do sobrevivente: {kit}\nKit do {sobrevivente}: {kit_daryl}")

elif sobrevivente == "Carol":
    print("Carol sabe como se esconder dos zumbis. Ela te dá uma ajuda.")
    kit.append("roupa_de_camuflagem")
    
    # Primeiro Dia
    itens_para_carol = kit[2:4]
    del kit[2:4]
    kit_carol.extend(itens_para_carol)
    
    # Segundo Dia
    itens_dados = kit[2:]
    kit = kit[:2]
    kit_carol.extend(itens_dados)
    print("Agora com as costas mais leves, podemos continuar com a nossa caminhada")
    
    # Terceiro Dia
    print("\nFinalmente chegamos em Alexandria!")
    print(f"\nUfa, podemos ficar aqui por um tempo,{sobrevivente}\n")
    print(f"Kit do sobrevivente: {kit}\nKit do {sobrevivente}: {kit_carol}")
