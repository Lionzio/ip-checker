# Solução gerada por IA (S42-04, ADR-08): groq, modelo openai/gpt-oss-20b, 17/10/2026.
# Só a partir do enunciado da L3-Q2, sem nenhum código de aluno. Revise antes do merge.
# L3-Q2: 🧢Rumo à Alexandria

kit_rick = ["colt_357", "distintivo", "radio_comunicador", "cantil", "curativo"]
kit_michonne = ["katana", "amolador", "binoculo", "faixa_curativo", "mapa"]
kit_daryl = ["arco e flecha", "flechas", "faca_de_caca", "corda", "carne_seca"]
kit_carol = ["facao", "bomba_de_fumaca", "sangue_zumbi", "fosforos", "biscoito"]

survivor_kit = ["taco_beisebol", "besta", "kit_medico", "feijao_enlatado",
                "walkie_talkie", "garrafa_agua", "biscoito"]

survivor = input().strip()

partner_kit = []
if survivor == "Rick":
    partner_kit = kit_rick.copy()
    print("Um grande líder sempre ajuda sua equipe, Rick lhe dá uma lanterna para a noite")
    survivor_kit.append("lanterna")
    # give taco_beisebol to Rick
    if "taco_beisebol" in survivor_kit:
        survivor_kit.remove("taco_beisebol")
        partner_kit.append("taco_beisebol")
    print(f"Kit atual sobrevivente: {survivor_kit}")
elif survivor == "Michonne":
    partner_kit = kit_michonne.copy()
    print("Michonne é uma ótima combatente, ela te dá uma arma para você não passar apertos.")
    if "kit_medico" in survivor_kit:
        survivor_kit.remove("kit_medico")
    print("Você usou o kit médico para socorrer Michonne!")
    print(f"Kit atual sobrevivente: {survivor_kit}")
elif survivor == "Daryl":
    partner_kit = kit_daryl.copy()
    print("Daryl é um ótimo caçador. Ele te dá carne para comer na refeição")
    # swap besta with arco e flecha
    if "besta" in survivor_kit:
        survivor_kit.remove("besta")
        partner_kit.append("besta")
    if "arco e flecha" in partner_kit:
        partner_kit.remove("arco e flecha")
        survivor_kit.append("arco e flecha")
    print(f"Kit atual sobrevivente: {survivor_kit}")
    print(f"Kit atual Daryl: {partner_kit}")
elif survivor == "Carol":
    partner_kit = kit_carol.copy()
    print("Carol sabe como se esconder dos zumbis. Ela te dá uma ajuda.")
    # give items at positions 2:4
    items_to_give = survivor_kit[2:4]
    survivor_kit = survivor_kit[:2] + survivor_kit[4:]
    partner_kit.extend(items_to_give)
else:
    # unknown survivor, just proceed with empty partner kit
    partner_kit = []

# Second day: split kit
rest = survivor_kit[2:]
survivor_kit = survivor_kit[:2]
partner_kit.extend(rest)
print("Agora com as costas mais leves, podemos continuar com a nossa caminhada")
print()

# Third day
print("Finalmente chegamos em Alexandria!")
print()
print(f"Ufa, podemos ficar aqui por um tempo,{survivor}")
print()
print(f"Kit do sobrevivente: {survivor_kit}")
print()
print(f"Kit do {survivor}: {partner_kit}")
