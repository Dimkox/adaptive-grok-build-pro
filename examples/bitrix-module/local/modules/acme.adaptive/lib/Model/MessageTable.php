<?php

declare(strict_types=1);

namespace Acme\Adaptive\Model;

use Bitrix\Main\ORM\Data\DataManager;
use Bitrix\Main\ORM\Fields\DatetimeField;
use Bitrix\Main\ORM\Fields\IntegerField;
use Bitrix\Main\ORM\Fields\StringField;

final class MessageTable extends DataManager
{
    public static function getTableName(): string
    {
        return 'acme_adaptive_message';
    }

    public static function getMap(): array
    {
        return [
            (new IntegerField('ID'))->configurePrimary()->configureAutocomplete(),
            (new StringField('MESSAGE'))->configureRequired()->configureSize(255),
            new DatetimeField('CREATED_AT'),
        ];
    }
}
