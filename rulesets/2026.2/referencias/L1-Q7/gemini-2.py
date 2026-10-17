# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L1-Q7, sem nenhum código de aluno. Revise antes do merge.
print("Depois que a Série A e a Libertadores ficaram só no sonho do Santa, Byte pendura a chuteira de ídolo tricolor e parte pro interior: começa a Excursão Interiorana em busca do time da sua vida!")

visitas_contaram = 0
gostou = 0
nao_gostou = 0

teve_catende = False
teve_palmares = False

for _ in range(2):
    caracteristica = input()
    veredito = input()
    
    eh_catende = "Catende" in caracteristica
    eh_palmares = "Palmares" in caracteristica
    
    if eh_catende:
        print("Catende!!! Aqui já rodou a maior usina de açúcar e álcool da América Latina, Byte sente o orgulho no ar.")
        teve_catende = True
    elif eh_palmares:
        print("Palmares, a Terra dos Poetas! Berço de nomes como Ascenso Ferreira, aqui até o futebol merece um verso.")
        teve_palmares = True
    else:
        visitas_contaram += 1
        if "Carcará" in caracteristica:
            print("Carcará no peito! Essa é terra de Salgueiro, o primeiro clube do interior a ser campeão pernambucano, Byte sente o chamado do Sertão!")
        elif "Patativa" in caracteristica:
            print("Show da Patativa! Caruaru e o Central esperam Byte de braços abertos, direto da maior feira a céu aberto do mundo!")
        elif "Azulão" in caracteristica:
            print("Ar puro de serra! O Azulão de Bonito, sensação recente do Pernambucano, pode ser o novo lar de Byte!")
        elif "fruticultura" in caracteristica:
            print("Margens do Velho Chico! Petrolina, a maior cidade do interior, com direito a manga, uva e muita irrigação, chama Byte pro time!")
        elif "Pássaro Preto" in caracteristica:
            print("Pertinho de casa! O Pássaro Preto, orgulhosamente um dos times mais folclóricos do planeta, também está de olho em Byte!")

    if veredito == "GOSTOU":
        print("Aquele cheirinho de interior fisgou o faro do Byte! Visita gostosa, mas ele quer conhecer mais um pouco antes de assinar.")
        gostou += 1
    elif veredito == "NÃO GOSTOU":
        print("Byte torceu o focinho dessa vez... não rolou clima pra ficar por aqui.")
        nao_gostou += 1

if teve_catende and teve_palmares:
    print("Catende e Palmares na excursão? Aí sim Byte tá garimpando ouro puro da Zona da Mata Sul! Pena que acabou por aqui.")

print()
print("RELATÓRIO DA EXCURSÃO SERTANEJA DO BYTE:")
print(f"- Visitas que contaram: {visitas_contaram}")
print(f"- Gostou: {gostou}")
print(f"- Não gostou: {nao_gostou}")
print()
print("E assim termina a Excursão Interiorana de Byte em Pernambuco. Anotar tudo isso na unha, sem laço nem lista, dá um trabalhão! Nas próximas férias, Byte espera que a molecada já saiba de laços, listas e funções pra dar conta do recado com estilo :)")
