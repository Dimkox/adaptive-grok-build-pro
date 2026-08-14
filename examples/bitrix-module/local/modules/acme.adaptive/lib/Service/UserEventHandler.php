<?php

declare(strict_types=1);

namespace Acme\Adaptive\Service;

final class UserEventHandler
{
    public static function onBeforeUserAdd(array &$fields): bool
    {
        $email = trim((string)($fields['EMAIL'] ?? ''));
        if ($email === '' || filter_var($email, FILTER_VALIDATE_EMAIL) === false) {
            global $APPLICATION;
            $APPLICATION->ThrowException('Invalid email');
            return false;
        }

        $fields['EMAIL'] = mb_strtolower($email);
        return true;
    }
}
