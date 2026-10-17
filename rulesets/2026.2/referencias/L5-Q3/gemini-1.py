# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L5-Q3, sem nenhum código de aluno. Revise antes do merge.
import sys


def main():
    print(
        "As sombras avançam sobre o Reino Celeste... É chegada a hora de reunir os heróis dispostos a enfrentar o Rei Demônio!"
    )

    herois = {}

    while True:
        nome = input().strip()
        if nome == "FIM":
            break
        linha_atrib = input().strip()
        # Exemplo: vida 50 - agilidade 30 - arma Espada Sagrada
        partes = linha_atrib.split(" - ")
        vida = int(partes[0].replace("vida", "").strip())
        agilidade = int(partes[1].replace("agilidade", "").strip())
        arma = partes[2].replace("arma", "").strip()

        herois[nome] = {"Vida": vida, "Agilidade": agilidade, "Arma": arma}

    if len(herois) < 3:
        print(
            "Poucos atenderam ao chamado do reino... Sem ao menos três heróis para formar a resistência, o Reino Celeste parece condenado à ruína!"
        )
        return

    print(
        "Os portões do castelo se abrem e os heróis marcham rumo ao campo de batalha. O confronto contra o Rei Demônio começa agora!"
    )

    demonio = {"Vida": 100, "Agilidade": 32, "Dano": 25}

    dano_armas = {
        "Espada Sagrada": 15,
        "Arco Lendário": 20,
        "Cajado Magistral": 25,
    }

    caidos = []
    ultimo_heroi_nome = None
    vitoria_herois = False
    derrota_herois = False

    while True:
        try:
            ataque_nome = input().strip()
        except EOFError:
            break

        if ataque_nome not in herois:
            print(
                "Nenhum herói com esse nome está no campo de batalha. O Rei Demônio aguarda impacientemente por seu próximo adversário!"
            )
            continue

        h = herois[ataque_nome]
        arma = h["Arma"]
        dano_heroi = dano_armas.get(arma, 0)
        tem_arma_valida = arma in dano_armas

        heroi_age_primeiro = h["Agilidade"] > demonio["Agilidade"]

        if heroi_age_primeiro:
            # Herói ataca primeiro
            if tem_arma_valida:
                print(
                    f"{ataque_nome} brandiu {arma} contra o Rei Demônio e causou {dano_heroi} pontos de dano!"
                )
                demonio["Vida"] -= dano_heroi
                if demonio["Vida"] <= 0:
                    vitoria_herois = True
                    ultimo_heroi_nome = ataque_nome
                    break
            else:
                print(
                    "A arma do herói não possui poder suficiente para atravessar a aura sombria do Rei Demônio!"
                )

            # Rei Demônio contra-ataca
            print(
                f"O Rei Demônio avançou com suas garras infernais e atingiu {ataque_nome}, causando 25 pontos de dano!"
            )
            h["Vida"] -= demonio["Dano"]
            if h["Vida"] <= 0:
                print(
                    f"{ataque_nome} tombou diante do poder do Rei Demônio!"
                )
                caidos.append(ataque_nome)
                del herois[ataque_nome]
                if not herois:
                    derrota_herois = True
                    break
        else:
            # Rei Demônio ataca primeiro
            print(
                f"O Rei Demônio avançou com suas garras infernais e atingiu {ataque_nome}, causando 25 pontos de dano!"
            )
            h["Vida"] -= demonio["Dano"]
            if h["Vida"] <= 0:
                print(
                    f"{ataque_nome} tombou diante do poder do Rei Demônio!"
                )
                caidos.append(ataque_nome)
                del herois[ataque_nome]
                if not herois:
                    derrota_herois = True
                    break
            else:
                # Herói ataca depois
                if tem_arma_valida:
                    print(
                        f"{ataque_nome} brandiu {arma} contra o Rei Demônio e causou {dano_heroi} pontos de dano!"
                    )
                    demonio["Vida"] -= dano_heroi
                    if demonio["Vida"] <= 0:
                        vitoria_herois = True
                        ultimo_heroi_nome = ataque_nome
                        break
                else:
                    print(
                        "A arma do herói não possui poder suficiente para atravessar a aura sombria do Rei Demônio!"
                    )

        if not herois:
            derrota_herois = True
            break

    if vitoria_herois:
        print(
            f"Com um golpe decisivo, {ultimo_heroi_nome} derrota o Rei Demônio! Após uma longa batalha, o Reino Celeste está finalmente livre de sua ameaça!"
        )
        if len(caidos) == 0:
            print(
                "Contra todas as expectativas, todos os heróis retornaram vivos ao Reino Celeste. Naquela noite, nenhuma nova inscrição precisou ser feita no Memorial dos Heróis."
            )
        else:
            print(
                "A vitória foi conquistada, mas teve seu preço. Alguns heróis não retornaram do campo de batalha e seus nomes serão eternizados no Memorial dos Heróis."
            )
    elif derrota_herois:
        print(
            "O último herói tombou. Vitorioso, o Rei Demônio retoma sua marcha sombria em direção ao Reino Celeste!"
        )

    if len(caidos) > 0:
        print("--- Memorial dos Heróis Caídos ---")
        for c in caidos:
            print(c)


if __name__ == "__main__":
    main()
