# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L3-Q2, sem nenhum código de aluno. Revise antes do merge.
kit_rick = ["colt_357", "distintivo", "radio_comunicador", "cantil", "curativo"]
kit_michonne = ["katana", "amolador", "binoculo", "faixa_curativo", "mapa"]
kit_daryl = ["arco e flecha","flechas","faca_de_caca", "corda", "carne_seca"]
kit_carol = ["facao", "bomba_de_fumaca", "sangue_zumbi", "fosforos", "biscoito"]

kit_sobrevivente = ["taco_beisebol", "besta", "kit_medico", "feijao_enlatado", "walkie_talkie", "garrafa_agua", "biscoito"]

sobrevivente = input().strip()

if sobrevivente == "Rick":
    print("Um grande líder sempre ajuda sua equipe, Rick lhe dá uma lanterna para a noite")
    kit_sobrevivente.append("lanterna")
    # Primeiro Dia: Rick precisará de sua ajuda. Dê a ele a sua arma (taco_beisebol) e a remova do seu kit.
    kit_sobrevivente.remove("taco_beisebol")
    print(f"Kit atual sobrevivente: {kit_sobrevivente}")

elif sobrevivente == "Michonne":
    print("Michonne é uma ótima combatente, ela te dá uma arma para você não passar apertos.")
    kit_sobrevivente.append("faca_afiada")
    # Primeiro Dia: Remova o "kit_medico" do seu kit para curá-la
    print("Você usou o kit médico para socorrer Michonne!")
    kit_sobrevivente.remove("kit_medico")
    print(f"Kit atual sobrevivente: {kit_sobrevivente}")

elif sobrevivente == "Daryl":
    print("Daryl é um ótimo caçador. Ele te dá carne para comer na refeição")
    kit_sobrevivente.append("carne")
    # Primeiro Dia: Troque a sua besta com o arco e flecha do Daryl
    kit_sobrevivente.remove("besta")
    kit_sobrevivente.append("arco e flecha")
    kit_daryl.remove("arco e flecha")
    kit_daryl.append("besta")
    print(f"   Kit atual sobrevivente: {kit_sobrevivente}")
    print(f"   Kit atual Daryl: {kit_daryl}")

elif sobrevivente == "Carol":
    print("Carol sabe como se esconder dos zumbis. Ela te dá uma ajuda.")
    kit_sobrevivente.append("roupa_de_camuflagem")
    # Primeiro Dia: adicione ao kit dela os seus itens que estão nas posições 2:4 (retire do seu kit)
    # Note que o enunciado pede itens nas posições 2:4 (índices 2 e 3).
    # Vamos pegar esses itens e adicionar ao kit_carol
    itens_para_carol = kit_sobrevivente[2:4]
    for item in itens_para_carol:
        kit_sobrevivente.remove(item)
        kit_carol.append(item)

# Segundo Dia: O seu kit ficará com apenas os 2 primeiros itens e o restante adicione ao kit do seu parceiro.
itens_restantes = kit_sobrevivente[2:]
kit_sobrevivente = kit_sobrevivente[:2]

if sobrevivente == "Rick":
    kit_rick.extend(itens_restantes)
    kit_parceiro_ref = kit_rick
    nome_parceiro = "Rick"
elif sobrevivente == "Michonne":
    kit_michonne.extend(itens_restantes)
    kit_parceiro_ref = kit_michonne
    nome_parceiro = "Michonne"
elif sobrevivente == "Daryl":
    kit_daryl.extend(itens_restantes)
    kit_parceiro_ref = kit_daryl
    nome_parceiro = "Daryl"
elif sobrevivente == "Carol":
    kit_carol.extend(itens_restantes)
    kit_parceiro_ref = kit_carol
    nome_parceiro = "Carol"

print("Agora com as costas mais leves, podemos continuar com a nossa caminhada\n")
print("Finalmente chegamos em Alexandria!\n")
print(f"Ufa, podemos ficar aqui por um tempo,{sobrevivente}\n")
print(f"Kit do sobrevivente: {kit_sobrevivente}\nKit do {nome_parceiro}: {kit_parceiro_ref}")
