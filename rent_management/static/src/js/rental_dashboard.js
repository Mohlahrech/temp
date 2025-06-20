/** @odoo-module */
import { registry} from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";
import { Component, onMounted, useState, useRef } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

class RentalDashboard extends Component {    static props = {
        // Client Action props
        action: { type: Object, optional: true },
        actionId: { type: [Number, Boolean], optional: true },
        className: { type: String, optional: true },
        updateActionState: { type: Function, optional: true },
        // Standard view props
        info: { type: Object, optional: true },
        resId: { type: [Number, Boolean], optional: true },
        resIds: { type: Array, optional: true },
        displayName: { type: String, optional: true },
        count: { type: Number, optional: true },
        mode: { type: String, optional: true },
        // Form view specific props
        globalState: { type: Object, optional: true },
        breadcrumbs: { type: Array, optional: true },
        display: { type: Object, optional: true },
        activeFields: { type: Object, optional: true },
        fields: { type: Object, optional: true }
    };    setup() {
        this.customer_creation = useRef('customer_creation');
        this.action = useService('action');
        this.orm = useService("orm");
        this.company = useService("company");
        this.state = useState({
            customerName: '',
            customerPhone: '',
            customerMail: '',
            lastName: '',
            firstName: '',
            birthDate: '',
            licenseNumber: '',
            licenseDate: '',
            licenseAuthority: '',
            isSaving: false,
            translations: {
                createRentalCustomer: _t('Create Rental Customer'),
                quickCreateSubtext: _t('Quickly add a new customer and create a rental contract.'),
                basicInfo: _t('Basic Information'),
                fullName: _t('Full Name'),
                phoneNumber: _t('Phone Number'),
                contactNumber: _t('Contact Number'),
                emailAddress: _t('Email Address'),
                emailPlaceholder: _t('name@example.com'),
                birthDate: _t('Birth Date'),
                personalInfo: _t('Personal Information'),
                firstName: _t('First Name'),
                lastName: _t('Last Name'),
                licenseInfo: _t("Driver's License Information"),
                licenseNumber: _t('License Number'),
                issueDate: _t('Issue Date'),
                issuingAuthority: _t('Issuing Authority'),
                createAndStart: _t('Create Customer & Start Rental'),
            }
        });

        onMounted(() => {
            this.showCustomerCreationForm();
        });
    }

    showCustomerCreationForm() {
        if (this.customer_creation.el) {
            this.customer_creation.el.classList.remove("d-none");
        } else {
            setTimeout(() => {
                if (this.customer_creation.el) {
                    this.customer_creation.el.classList.remove("d-none");
                }
            }, 0);
        }
    }    async saveCustomer() {
        if (this.state.isSaving) {
            return; // Prevent double submission
        }

        try {
            this.state.isSaving = true;
            const data = await this.fetch_customer_data();

            const createResult = await this.orm.create('res.partner', [data]);
            let newCustomerId = null;
            
            if (Array.isArray(createResult) && createResult.length > 0) {
                newCustomerId = createResult[0];
            } else if (typeof createResult === 'number') {
                newCustomerId = createResult;
            }            if (typeof newCustomerId === 'number' && newCustomerId > 0) {
                this.action.doAction({
                    type: 'ir.actions.act_window',
                    res_model: 'sale.order',
                    views: [[false, 'form']],
                    target: 'current',
                    context: {
                        'default_partner_id': newCustomerId
                    }
                });
                this.state.isSaving = false;
            } else {
                console.error("Invalid or no Customer ID extracted:", newCustomerId);
                alert(_t("Customer created, but failed to get valid ID. Cannot open rental form."));
            }
        } catch (error) {
            console.error("Error:", error);
            if (error.message === 'Missing required fields') {
                // Already handled with alert in fetch_customer_data
                return;
            }
            if (error.data && error.data.message) {
                alert(_t(`Error: ${error.data.message}`));
            } else {
                alert(_t("Failed to create customer record. Please check all required fields and try again."));
            }
            this.state.isSaving = false;
        }
    }    fetch_customer_data() {
        const missingFields = [];
          // Get and validate required fields
        const name = this.state.customerName.trim();
        const phone = this.state.customerPhone.trim();
        const lastName = this.state.lastName.trim();
        const firstName = this.state.firstName.trim();

        if (!name) missingFields.push(_t('Full Name'));
        if (!phone) missingFields.push(_t('Phone Number'));
        if (!lastName) missingFields.push(_t('Last Name'));
        if (!firstName) missingFields.push(_t('First Name'));

        if (missingFields.length > 0) {
            alert(_t("Please fill in all required fields:\n") + missingFields.map(field => `- ${field}`).join('\n'));
            throw new Error('Missing required fields');
        }        // Prepare base data with required fields
        const data = {
            name: name,
            phone: phone,
            nom: lastName,
            prenom: firstName,
            company_type: 'person',
            is_customer: true,
            company_id: this.company.currentCompany.id
        };
        
        // Add optional fields only if they have values
        const optionalFields = {
            email: this.state.customerMail.trim(),
            date_naissance: this.state.birthDate,
            permis_numero: this.state.licenseNumber.trim(),
            permis_date: this.state.licenseDate,
            permis_lieu: this.state.licenseAuthority.trim()
        };

        // Add optional fields that have values
        Object.entries(optionalFields).forEach(([key, value]) => {
            if (value && value !== '') {
                data[key] = value;
            }
        });

        return data;    }
}

RentalDashboard.template = "rent_management.RentalDashboard";

// Register the client action
registry.category("actions").add("rent_management.rental_dashboard", RentalDashboard);

// Also register as a component for reuse
registry.category("components").add("RentalDashboard", RentalDashboard);
