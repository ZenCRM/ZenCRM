/* Settings component section; state is created for each CRM instance. */
window.ZenSettings = window.ZenSettings || {};
window.ZenSettings.state = function () { return {
        permissionCatalog: [],
        managedRoles: [],
        roleRules: {},
        teamRules: {},
        permissionSubject: 'role:manager',
        permissionError: '',
        permissionSaved: '',
        newRoleName: '',
        roleNameDraft: '',
        effectivePermissions: {},
        menuPermissionsState: {},
        savingMenuSettings: false,
        menuSettingsSaved: false,

        leadSources: ['Strona WWW', 'Polecenie', 'Telefon', 'Social Media', 'Kampania Google', 'Inne'],
        newLeadSourceName: '',
        editingLeadSourceIndex: null,
        editingLeadSourceName: '',
        leadWebhookEnabled: false,
        leadWebhookToken: '',
        savingLeadSettings: false,
        leadSettingsSaved: false,
}; };
