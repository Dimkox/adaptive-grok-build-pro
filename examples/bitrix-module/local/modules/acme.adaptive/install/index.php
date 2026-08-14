<?php

declare(strict_types=1);

use Acme\Adaptive\Model\MessageTable;
use Acme\Adaptive\Service\UserEventHandler;
use Bitrix\Main\Application;
use Bitrix\Main\Context;
use Bitrix\Main\EventManager;
use Bitrix\Main\Localization\Loc;
use Bitrix\Main\ModuleManager;

Loc::loadMessages(__FILE__);

require_once dirname(__DIR__) . '/lib/Model/MessageTable.php';
require_once dirname(__DIR__) . '/lib/Service/UserEventHandler.php';

class acme_adaptive extends CModule
{
    public $MODULE_ID = 'acme.adaptive';
    public $MODULE_VERSION;
    public $MODULE_VERSION_DATE;
    public $MODULE_NAME;
    public $MODULE_DESCRIPTION;

    public function __construct()
    {
        $arModuleVersion = [];
        include __DIR__ . '/version.php';
        $this->MODULE_VERSION = (string)($arModuleVersion['VERSION'] ?? '1.0.0');
        $this->MODULE_VERSION_DATE = (string)($arModuleVersion['VERSION_DATE'] ?? '2026-08-14 00:00:00');
        $this->MODULE_NAME = Loc::getMessage('ACME_ADAPTIVE_MODULE_NAME') ?: 'Adaptive example';
        $this->MODULE_DESCRIPTION = Loc::getMessage('ACME_ADAPTIVE_MODULE_DESCRIPTION') ?: 'Reference D7 module';
    }

    public function DoInstall(): void
    {
        ModuleManager::registerModule($this->MODULE_ID);
        $this->installDatabase();
        $this->registerHandlers();
    }

    public function DoUninstall(): void
    {
        $this->unregisterHandlers();
        CAgent::RemoveModuleAgents($this->MODULE_ID);

        $request = Context::getCurrent()->getRequest();
        if ($request->getPost('savedata') !== 'Y') {
            $this->uninstallDatabase();
        }

        ModuleManager::unRegisterModule($this->MODULE_ID);
    }

    private function registerHandlers(): void
    {
        EventManager::getInstance()->registerEventHandlerCompatible(
            'main',
            'OnBeforeUserAdd',
            $this->MODULE_ID,
            UserEventHandler::class,
            'onBeforeUserAdd'
        );
    }

    private function unregisterHandlers(): void
    {
        EventManager::getInstance()->unRegisterEventHandler(
            'main',
            'OnBeforeUserAdd',
            $this->MODULE_ID,
            UserEventHandler::class,
            'onBeforeUserAdd'
        );
    }

    private function installDatabase(): void
    {
        $connection = Application::getConnection();
        if (!$connection->isTableExists(MessageTable::getTableName())) {
            MessageTable::getEntity()->createDbTable();
        }
    }

    private function uninstallDatabase(): void
    {
        $connection = Application::getConnection();
        if ($connection->isTableExists(MessageTable::getTableName())) {
            $connection->dropTable(MessageTable::getTableName());
        }
    }
}
