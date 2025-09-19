# Habblive - Automatic Login
Log in quickly (to keep your nickname) or log in permanently (to earn achievements or fill rooms) at Habblive.in
<img src="https://i.imgur.com/kk5rGi7.png" width="256" height="192">

### 📖 How to use

1. [Fork this repository](https://github.com/MauricioFFJ/Habblive-Auto-Login/fork);
2. Go to your forked repository;
3. Go to Settings > Secrets and Variables > Actions . And click the button `New Repository Secret`;
4. For the secret name, you will use `HABBLIVE_USERNAME_1` (nickname) and `HABBLIVE_PASSWORD_1` (account password). This repository supports up to 50 accounts, and can replace the number 1 from 1 to 50;
5. Go the your forked repository and go the Actions tab and press the button `I understand my workflows, go ahead and enable them`;

**🚩 Attention:** Saving your credentials as secret names on GitHub keeps your accounts secure, even if the repository is public!

## 🔥 Workflows

### 🛎️ Daily Habblive Login

This project uses GitHub Actions scheduled workflow to keep your nickname alive. Every day at **03:00 (Brasília time)**, accounts added in `Secrets and Variables` will briefly log in to the Habblive client, keeping their accounts active and preventing them from being inactive for months and having their nicknames put up for sale. The workflow can be viewed [here](.github/workflows/login.yml).

### 🆙 Persistent Login

This project uses GitHub Actions scheduled workflow to keep your active accounts indefinitely. In case of redirections or client outages, the accounts always re-enter automatically.
To configure the desired actions, access the code [here](persistent_login.py).

**NOTE:** Persistent Login is active for an average of 6 hours and must be reactivated after that period. If you want it to reactivate automatically, add the `HABILITAR_REINICIO` variable to the value `true` in `Settings` - `Secrets and Variables` - `Actions` - `Variables`.

Just make changes to the following snippet:

```py
# ===== CONFIGURAÇÃO =====
EXECUTAR_ACOES = True  # True = faz ações no quarto, False = só loga/reloga (Cafofo ou Vista do Hotel)

# Configurações personalizadas
DONO_QUARTO = "NICKNAME"    # Nome do dono do quarto.
NOME_QUARTO = "ROOM NAME"   # Nome exato do quarto.
# ========================
 ```
`EXECUTAR_ACOES` **True** = performs actions in the room, **False** = only logs in/logs back (Hotel Room or View);

`DONO_QUARTO` Name of the room owner **(If `EXECUTAR_ACOES` is true)**;

`NOME_QUARTO` Exact name of the room **(If `EXECUTAR_ACOES` is true)**.

## ⚠️ Caveats

- This project aims to keep your account nicknames safe and to allow you to log in to a large number of accounts for the purpose of filling rooms or progressing your achievements.
- Use at your own risk and use in moderation. We are not responsible for penalties from the Habblive.in staff team in case of misuse of this project.
- This project may stop working if Habblive is updated. The last update was on `September 19, 2025`. **Follow the updates in the official repository [here](https://github.com/MauricioFFJ/Habblive-Auto-Login/).**

Project created by: **@EuSolitudine**

<a href="https://x.com/@EuSolitudine" target="_blank">
  <img src="https://img.shields.io/badge/Follow me on X-000000?style=for-the-badge&logo=x&logoColor=white" alt="@EuSolitudine">
</a>
