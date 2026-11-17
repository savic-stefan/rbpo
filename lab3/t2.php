<?php

if (isset($_GET['Login'])) {

    // Проверка входных параметров (раньше был прямой доступ -> Notice + CWE-20)
    $user = isset($_GET['username']) ? $_GET['username'] : '';
    $pass = isset($_GET['password']) ? $_GET['password'] : '';

    // Безопасное хеширование (раньше был md5 -> CWE-328)
    $passHash = password_hash($pass, PASSWORD_DEFAULT);

    // Подготовленный запрос (раньше была SQL-инъекция -> CWE-89)
    $stmt = mysqli_prepare(
        $GLOBALS["___mysqli_ston"],
        "SELECT user, avatar, password FROM users WHERE user = ? LIMIT 1"
    );
    mysqli_stmt_bind_param($stmt, "s", $user);
    mysqli_stmt_execute($stmt);
    $result = mysqli_stmt_get_result($stmt);

    // Проверяем найденного пользователя
    if ($result && mysqli_num_rows($result) === 1) {

        $row = mysqli_fetch_assoc($result);

        // Проверка пароля безопасным способом (раньше просто сравнивали md5 -> CWE-759)
        if (password_verify($pass, $row["password"])) {

            // Экранирование вывода (раньше был XSS -> CWE-79)
            $safeUser   = htmlspecialchars($row["user"], ENT_QUOTES, "UTF-8");
            $safeAvatar = htmlspecialchars($row["avatar"], ENT_QUOTES, "UTF-8");

            $html  = "<p>Welcome to the password protected area {$safeUser}</p>";
            $html .= "<img src=\"{$safeAvatar}\" />";

        } else {
            // Ошибка входа (не выдаём инфу о БД -> CWE-209)
            $html = "<pre><br />Username and/or password incorrect.</pre>";
        }

    } else {
        // CWE-209 (Информационная утечка) 
        $html = "<pre><br />Username and/or password incorrect.</pre>";
    }

    // Нормальное закрытие соединения (CWE-710)
    mysqli_stmt_close($stmt);
    mysqli_close($GLOBALS["___mysqli_ston"]);
}

?>

