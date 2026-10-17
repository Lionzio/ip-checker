# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L1-Q8, sem nenhum código de aluno. Revise antes do merge.
import math

print("Byte: Au! Vou conseguir esse ovo!!")

# Fase 1: Exploração
fase1 = input()

# Inicializações
perigo = 30 if fase1.isupper() else 10
timer = len(fase1) * 5

fase1_lower = fase1.lower()
tem_ferro = "ferro" in fase1_lower
tem_monstros = "monstros" in fase1_lower
tem_diamante = "diamante" in fase1_lower
tem_ouro = "ouro" in fase1_lower
tem_estrutura = "estrutura" in fase1_lower

tem_camas = False
portal_ruinas = False
enfrentou_troia = False

if tem_monstros:
    print("Você não pode dormir agora, há monstros por perto.")
    perigo += 25
    timer += 20
    if "4" in fase1:
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

if tem_estrutura:
    est = input().lower()
    if "vila" in est:
        print("Byte desbloqueou a conquista: [Negócio Fechado!]")
        timer += 10
        tem_camas = True
    if "portal" in est:
        portal_ruinas = True
    if "templo" in est:
        perigo += 100
    if "mansao" in est or "mansão" in est:
        if perigo > 100:
            print("Byte desbloqueou a conquista: [À beira da Morte]")
        perigo -= 150
        timer += 40
    if "camara" in est or "câmara" in est:
        print("Byte desbloqueou a conquista: [Minecraft: Jogos Vorazes]")
        timer += 60
        perigo += 50

# Normalizar perigo
if perigo < 0:
    perigo = 0

morto = False
if perigo > 100:
    morto = True

if not morto:
    print(
        f"Byte: Ufa, finally acabei, demorei apenas {timer} minutos, vamos ao Nether!".replace(
            "finally", "finalmente"
        )
    )

    # Fase 2: O Nether
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
        if tem_ferro or tem_ouro:
            print("Byte desbloqueou a conquista: [Meu precioso!]")
            perigo += 10
        else:
            perigo += 20
            timer += 30

    resultado_blaze = input().strip()
    try:
        val_blaze = float(resultado_blaze)
        if val_blaze.is_integer():
            val_blaze = int(val_blaze)
            if 1 <= val_blaze <= 12:
                timer += 20
            elif val_blaze > 12:
                timer -= 10
            else:
                timer += 30
                perigo += 40
        else:
            timer += 30
            perigo += 40
    except ValueError:
        timer += 30
        perigo += 40

    if perigo < 0:
        perigo = 0
    if perigo > 100:
        morto = True

    if not morto:
        # Fase 3: O Fim?
        perigo -= 20
        if perigo < 0:
            perigo = 0

        x = int(input())
        z = int(input())

        xbyte, zbyte = 100, 200
        dist = math.isqrt((xbyte - x) ** 2 + (zbyte - z) ** 2)
        print(f"Byte: Estou a {dist} blocos da Stronghold!")

        timer += dist * 2
        perigo += 30

        if perigo > 100:
            morto = True

        sucesso_ovo = False
        if not morto:
            if timer > 300:  # > 5 horas
                print("Troia desbloqueou a conquista: [Liberte o End]")
                print("Byte desbloqueou a conquista: [É o fim?]")
            elif 180 < timer <= 300:  # Entre 3 e 5 horas
                enfrentou_troia = True
                print("Troia desbloqueou a conquista: [É o fim?]")
                print("Byte desbloqueou a conquista: [É o fim?]")

                n_flechas = int(input())
                n_alvos = int(input())

                if n_alvos == 1:
                    print("Byte: Troia já destruiu todos os cristais, agora é só o Dragão...")
                
                div = n_flechas / n_alvos
                if div.is_integer() and int(div) > 0:
                    if n_flechas == 1 and n_alvos == 1:
                        print("Byte: Uma flecha, Uma chance.")
                    timer += 10
                    print("Byte desbloqueou a conquista: [Liberte o End]")
                    sucesso_ovo = True
                else:
                    print("Byte: Droga! Não tenha flechas suficientes, Troia vai ganhar...")
                    timer += 20
            else:  # < 3 horas
                print("Byte desbloqueou a conquista: [É o fim?]")
                timer += 5
                if tem_camas:
                    print("Byte: Como eu amo o [Design Intencional do Jogo]!")
                print("Byte desbloqueou a conquista: [Liberte o End]")
                sucesso_ovo = True

            if morto:
                print("Byte foi morto.")
                print("Byte: auu.... Não consegui pegar o ovo...")
            elif sucesso_ovo:
                print("Byte desbloqueou a conquista: [A nova geração]")
                print("Byte: Aauauau! O ovo é meu! que rolem os créditos!")
            else:
                print("Byte: auu.... Não consegui pegar o ovo...")
        else:
            print("Byte foi morto.")
            print("Byte: auu.... Não consegui pegar o ovo...")
    else:
        print("Byte foi morto.")
        print("Byte: auu.... Não consegui pegar o ovo...")
else:
    print("Byte foi morto.")
    print("Byte: auu.... Não consegui pegar o ovo...")

if perigo < 0:
    perigo = 0

print()
print("🚨Avaliação de nível de perigo: ", end="")
if perigo == 100 or enfrentou_troia:
    print("Odisseia de Byte.")
elif perigo > 100:
    print("Letal.")
elif perigo >= 70:
    print("Aventura Perigosa.")
elif perigo >= 30:
    print("Jornada Complicada.")
else:
    print("Passeio no Parque.")

hora = timer // 60
minutos = timer % 60
print()
print(f"Timer: {hora} h e {minutos} minutos")
