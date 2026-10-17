# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L5-Q3, sem nenhum código de aluno. Revise antes do merge.
def main():
    print("As sombras avançam sobre o Reino Celeste... É chegada a hora de reunir os heróis dispostos a enfrentar o Rei Demônio!")

    herois = {}
    
    while True:
        linha = input().strip()
        if linha == "FIM":
            break
        nome = linha
        atributos_linha = input().strip()
        
        partes = atributos_linha.split(" - ")
        vida = int(partes[0].split()[1])
        agilidade = int(partes[1].split()[1])
        arma = partes[2].split("arma ")[1]
        
        herois[nome] = {
            "Vida": vida,
            "Agilidade": agilidade,
            "Arma": arma
        }

    if len(herois) < 3:
        print("Poucos atenderam ao chamado do reino... Sem ao menos três heróis para formar a resistência, o Reino Celeste parece condenado à ruína!")
        return

    print("Os portões do castelo se abrem e os heróis marcham rumo ao campo de batalha. O confronto contra o Rei Demônio começa agora!")

    demonio = {
        "Vida": 100,
        "Agilidade": 32,
        "Dano": 25
    }

    dano_armas = {
        "Espada Sagrada": 15,
        "Arco Lendário": 20,
        "Cajado Magistral": 25
    }

    caidos = []
    herois_vivos = list(herois.keys())
    herois_totais_iniciais = len(herois)

    while demonio["Vida"] > 0 and len(herois_vivos) > 0:
        atacante = input().strip()
        
        if atacante not in herois_vivos:
            print("Nenhum herói com esse nome está no campo de batalha. O Rei Demônio aguarda impacientemente por seu próximo adversário!")
            continue

        h_data = herois[atacante]
        arma = h_data["Arma"]
        agil_heroi = h_data["Agilidade"]
        agil_demonio = demonio["Agilidade"]

        if agil_heroi > agil_demonio:
            # Herói ataca primeiro
            if arma in dano_armas:
                dano = dano_armas[arma]
                demonio["Vida"] -= dano
                print(f"{atacante} brandiu {arma} contra o Rei Demônio e causou {dano} pontos de dano!")
                if demonio["Vida"] <= 0:
                    break
            else:
                print("A arma do herói não possui poder suficiente para atravessar a aura sombria do Rei Demônio!")
            
            # Rei retruca se vivo
            if demonio["Vida"] > 0:
                h_data["Vida"] -= demonio["Dano"]
                print(f"O Rei Demônio avançou com suas garras infernais e atingiu {atacante}, causando 25 pontos de dano!")
                if h_data["Vida"] <= 0:
                    print(f"{atacante} tombou diante do poder do Rei Demônio!")
                    caidos.append(atacante)
                    herois_vivos.remove(atacante)
        else:
            # Demônio ataca primeiro
            h_data["Vida"] -= demonio["Dano"]
            print(f"O Rei Demônio avançou com suas garras infernais e atingiu {atacante}, causando 25 pontos de dano!")
            if h_data["Vida"] <= 0:
                print(f"{atacante} tombou diante do poder do Rei Demônio!")
                caidos.append(atacante)
                herois_vivos.remove(atacante)
            else:
                # Herói retruca
                if arma in dano_armas:
                    dano = dano_armas[arma]
                    demonio["Vida"] -= dano
                    print(f"{atacante} brandiu {arma} contra o Rei Demônio e causou {dano} pontos de dano!")
                    if demonio["Vida"] <= 0:
                        break
                else:
                    print("A arma do herói não possui poder suficiente para atravessar a aura sombria do Rei Demônio!")

    # Resultado da Batalha
    if demonio["Vida"] <= 0:
        print(f"Com um golpe decisivo, {atacante} derrota o Rei Demônio! Após uma longa batalha, o Reino Celeste está finalmente livre de sua ameaça!")
        if len(caidos) == 0:
            print("Contra todas as expectativas, todos os heróis retornaram vivos ao Reino Celeste. Naquela noite, nenhuma nova inscrição precisou ser feita no Memorial dos Heróis.")
        else:
            print("A vitória foi conquistada, mas teve seu preço. Alguns heróis não retornaram do campo de batalha e seus nomes serão eternizados no Memorial dos Heróis.")
    else:
        print("O último herói tombou. Vitorioso, o Rei Demônio retoma sua marcha sombria em direção ao Reino Celeste!")

    if len(caidos) > 0:
        print("--- Memorial dos Heróis Caídos ---")
        for c in caidos:
            print(c)

if __name__ == "__main__":
    main()
