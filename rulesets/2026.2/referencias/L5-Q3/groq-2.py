# Solução gerada por IA (S42-04, ADR-08): groq, modelo openai/gpt-oss-20b, 17/10/2026.
# Só a partir do enunciado da L5-Q3, sem nenhum código de aluno. Revise antes do merge.
import sys

def main():
    lines = [line.rstrip('\n') for line in sys.stdin]
    idx = 0
    heroes = {}
    relics = {"Espada Sagrada": 15, "Arco Lendário": 20, "Cajado Magistral": 25}
    # Read heroes
    while idx < len(lines):
        name = lines[idx].strip()
        idx += 1
        if name == "FIM":
            break
        if idx >= len(lines):
            break
        attr_line = lines[idx].strip()
        idx += 1
        parts = [p.strip() for p in attr_line.split(' - ')]
        vida = agi = None
        arma = None
        for p in parts:
            if p.startswith('vida'):
                vida = int(p.split()[1])
            elif p.startswith('agilidade'):
                agi = int(p.split()[1])
            elif p.startswith('arma'):
                arma = p.split(' ', 1)[1]
        heroes[name] = {"Vida": vida, "Agilidade": agi, "Arma": arma}
    # Output initial message
    print("As sombras avançam sobre o Reino Celeste... É chegada a hora de reunir os heróis dispostos a enfrentar o Rei Demônio!")
    if len(heroes) < 3:
        print("Poucos atenderam ao chamado do reino... Sem ao menos três heróis para formar a resistência, o Reino Celeste parece condenado à ruína!")
        return
    print("Os portões do castelo se abrem e os heróis marcham rumo ao campo de batalha. O confronto contra o Rei Demônio começa agora!")
    demon_life = 100
    demon_agi = 32
    demon_damage = 25
    fallen = []
    last_attacker = None
    # Battle loop
    while demon_life > 0 and heroes:
        if idx >= len(lines):
            break
        hero_name = lines[idx].strip()
        idx += 1
        if hero_name not in heroes:
            print("Nenhum herói com esse nome está no campo de batalha. O Rei Demônio aguarda impacientemente por seu próximo adversário!")
            continue
        hero = heroes[hero_name]
        hero_agi = hero["Agilidade"]
        hero_arma = hero["Arma"]
        # Determine order
        hero_first = hero_agi > demon_agi
        if hero_first:
            # Hero attacks first
            dmg = relics.get(hero_arma, 0)
            if dmg > 0:
                demon_life -= dmg
                print(f"{hero_name} brandiu {hero_arma} contra o Rei Demônio e causou {dmg} pontos de dano!")
                if demon_life <= 0:
                    last_attacker = hero_name
                    break
            else:
                print("A arma do herói não possui poder suficiente para atravessar a aura sombria do Rei Demônio!")
            # Demon attacks if still alive
            if demon_life > 0:
                hero["Vida"] -= demon_damage
                print(f"O Rei Demônio avançou com suas garras infernais e atingiu {hero_name}, causando 25 pontos de dano!")
                if hero["Vida"] <= 0:
                    fallen.append(hero_name)
                    del heroes[hero_name]
                    print(f"{hero_name} tombou diante do poder do Rei Demônio!")
        else:
            # Demon attacks first
            hero["Vida"] -= demon_damage
            print(f"O Rei Demônio avançou com suas garras infernais e atingiu {hero_name}, causando 25 pontos de dano!")
            if hero["Vida"] <= 0:
                fallen.append(hero_name)
                del heroes[hero_name]
                print(f"{hero_name} tombou diante do poder do Rei Demônio!")
                continue
            # Hero attacks
            dmg = relics.get(hero_arma, 0)
            if dmg > 0:
                demon_life -= dmg
                print(f"{hero_name} brandiu {hero_arma} contra o Rei Demônio e causou {dmg} pontos de dano!")
                if demon_life <= 0:
                    last_attacker = hero_name
                    break
            else:
                print("A arma do herói não possui poder suficiente para atravessar a aura sombria do Rei Demônio!")
    # Outcome
    if demon_life <= 0:
        print(f"Com um golpe decisivo, {last_attacker} derrota o Rei Demônio! Após uma longa batalha, o Reino Celeste está finalmente livre de sua ameaça!")
        if fallen:
            print("A vitória foi conquistada, mas teve seu preço. Alguns heróis não retornaram do campo de batalha e seus nomes serão eternizados no Memorial dos Heróis.")
        else:
            print("Contra todas as expectativas, todos os heróis retornaram vivos ao Reino Celeste. Naquela noite, nenhuma nova inscrição precisou ser feita no Memorial dos Heróis.")
        if fallen:
            print("--- Memorial dos Heróis Caídos ---")
            for name in fallen:
                print(name)
    else:
        print("O último herói tombou. Vitorioso, o Rei Demônio retoma sua marcha sombria em direção ao Reino Celeste!")
        if fallen:
            print("--- Memorial dos Heróis Caídos ---")
            for name in fallen:
                print(name)

if __name__ == "__main__":
    main()
