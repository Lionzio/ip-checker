# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L1-Q8, sem nenhum código de aluno. Revise antes do merge.
print("Byte: Au! Vou conseguir esse ovo!!")

s_fase1 = input()
timer = len(s_fase1) * 5

perigo = 30 if s_fase1 == s_fase1.upper() and len(s_fase1) > 0 else 10

tem_ferro = "ferro" in s_fase1.lower()
tem_diamante = "diamante" in s_fase1.lower()
tem_ouro = "ouro" in s_fase1.lower()
tem_monstro = "monstros" in s_fase1.lower()
tem_estrutura = "estrutura" in s_fase1.lower()

tem_camas = False

if tem_monstro:
    print("Você não pode dormir agora, há monstros por perto.")
    perigo += 25
    timer += 20
    if "4" in s_fase1:
        print("Byte desbloqueou a conquista: [Caçador de Monstros]")
        perigo *= 2

if tem_ferro:
    print("Byte desbloqueou a conquista: [A Idade do Ferro]")
    perigo -= 15
    timer += 5

if tem_diamante:
    if tem_ferro:
        print("Byte desbloqueou a conquista: [Diamantes!]")
        perigo -= 40
    else:
        timer += 15

if tem_ouro:
    if tem_ferro:
        timer += 10
    else:
        timer += 5

portal_ruinas = False

if tem_estrutura:
    est = input().lower()
    if "vila" in est:
        print("Byte desbloqueou a conquista: [Negócio Fechado!]")
        tem_camas = True
        timer += 10
    if "portal" in est:
        portal_ruinas = True
    if "templo" in est:
        perigo += 100
    if "mansao" in est:
        if perigo > 100:
            print("Byte desbloqueou a conquista: [À beira da Morte]")
        perigo -= 150
        timer += 40
    if "camara" in est:
        print("Byte desbloqueou a conquista: [Minecraft: Jogos Vorazes]")
        timer += 60
        perigo += 50

if perigo < 0:
    perigo = 0

morto = False
if perigo > 100:
    morto = True

if not morto:
    print(
        f"Byte: Ufa, finalmente acabei, demorei apenas {timer} minutos, vamos ao Nether!"
    )

    if not portal_ruinas:
        print("Byte desbloqueou a conquista: [Entrando numa fria]")
        timer += 5

    print("Byte desbloqueou a conquista: [O buraco é mais embaixo]")
    perigo += 30

    n1 = float(input())
    n2 = float(input())

    soma = n1 + n2
    if soma.is_integer():
        pass
    else:
        if tem_ouro:
            print("Byte desbloqueou a conquista: [Meu precioso!]")
            perigo += 10
        else:
            perigo += 20
            timer += 30

    res_blaze = input()
    if res_blaze.isdigit() and 1 <= int(res_blaze) <= 12:
        timer += 20
    elif res_blaze.isdigit() and int(res_blaze) > 12:
        timer -= 10
    else:
        timer += 30
        perigo += 40

    if perigo < 0:
        perigo = 0
    if perigo > 100:
        morto = True

if not morto:
    perigo -= 20
    if perigo < 0:
        perigo = 0

    x = int(input())
    z = int(input())

    dist2 = (100 - x) ** 2 + (200 - z) ** 2
    dist = int(dist2**0.5)
    print(f"Byte: Estou a {dist} blocos da Stronghold!")
    timer += dist * 2

    perigo += 30
    if perigo < 0:
        perigo = 0
    if perigo > 100:
        morto = True

enfrentou_troia = False
conseguiu_ovo = False

if not morto:
    print("Byte desbloqueou a conquista: [É o fim?]")
    if timer > 300:
        morto = True
    elif tem_camas:
        print("Byte: Como eu amo o [Design Intencional do Jogo]!")
        perigo -= 30
        if perigo < 0:
            perigo = 0
        conseguiu_ovo = True
    elif 180 < timer <= 300:
        enfrentou_troia = True
        print("Troia desbloqueou a conquista: [É o fim?]")
        nf = int(input())
        na = int(input())
        if na == 1:
            print("Byte: Troia já destruiu todos os cristais, agora é só o Dragão...")
        if nf > 0 and (nf / na).is_integer() and (nf // na) > 0:
            print("Byte: Uma flecha, Uma chance.")
            timer += 10
            print("Byte desbloqueou a conquista: [Liberte o End]")
            conseguiu_ovo = True
        else:
            print("Byte: Droga! Não tenha flechas suficientes, Troia vai ganhar...")
            timer += 20
    else:
        timer += 5
        print("Byte desbloqueou a conquista: [Liberte o End]")
        conseguiu_ovo = True

if morto or not conseguiu_ovo:
    if morto:
        print("Byte foi morto.")
    print("Byte: auu.... Não consegui pegar o ovo...")
else:
    print("Byte desbloqueou a conquista: [A nova geração]")
    print("Byte: Aauauau! O ovo é meu! que rolem os créditos!")

print()
print("🚨Avaliação de nível de perigo: ", end="")
if perigo >= 100 or enfrentou_troia:
    print("Odisseia de Byte.")
elif perigo > 100:
    print("Letal.")
elif perigo < 30:
    print("Passeio no Parque.")
elif 30 <= perigo < 70:
    print("Jornada Complicada.")
elif 70 <= perigo < 100:
    print("Aventura Perigosa.")

horas = timer // 60
minutos = timer % 60
print()
print(f"Timer: {horas} h e {minutos} minutos")
