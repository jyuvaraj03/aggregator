export interface paths {
    "/accounts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Accounts */
        get: operations["list_accounts_accounts_get"];
        put?: never;
        /** Create Account */
        post: operations["create_account_accounts_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/accounts/{account_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Account */
        get: operations["get_account_accounts__account_id__get"];
        put?: never;
        post?: never;
        /** Remove Account */
        delete: operations["remove_account_accounts__account_id__delete"];
        options?: never;
        head?: never;
        /** Update Account */
        patch: operations["update_account_accounts__account_id__patch"];
        trace?: never;
    };
    "/emails": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Emails */
        get: operations["list_emails_emails_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/emails/{email_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Email */
        get: operations["get_email_emails__email_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/templates": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Templates */
        get: operations["list_templates_templates_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/templates/{template_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Template */
        get: operations["get_template_templates__template_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/templates/{template_id}/account": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Update Template Account */
        put: operations["update_template_account_templates__template_id__account_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/templates/{template_id}/field-parsers": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Field Parsers */
        get: operations["get_field_parsers_templates__template_id__field_parsers_get"];
        /** Put Field Parsers */
        put: operations["put_field_parsers_templates__template_id__field_parsers_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/templates/{template_id}/field-parsers/approve": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Post Approve Field Parsers */
        post: operations["post_approve_field_parsers_templates__template_id__field_parsers_approve_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/templates/{template_id}/field-parsers/generate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Post Generate Field Parsers */
        post: operations["post_generate_field_parsers_templates__template_id__field_parsers_generate_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/email-sync": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Sync Email */
        post: operations["sync_email_email_sync_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/transaction-extraction": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Extract Transactions Action */
        post: operations["extract_transactions_action_transaction_extraction_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/transactions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Transactions */
        get: operations["list_transactions_transactions_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/jobs/{job_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Job */
        get: operations["get_job_jobs__job_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** AccountCreate */
        AccountCreate: {
            /** Name */
            name: string;
        };
        /** AccountPage */
        AccountPage: {
            /** Items */
            items: components["schemas"]["AccountResponse"][];
            /** Total */
            total: number;
            /** Page */
            page: number;
            /** Page Size */
            page_size: number;
            /** Total Pages */
            total_pages: number;
        };
        /** AccountResponse */
        AccountResponse: {
            /** Id */
            id: number;
            /** Name */
            name: string;
        };
        /** AccountUpdate */
        AccountUpdate: {
            /** Name */
            name: string;
        };
        /** BackgroundJobResponse */
        BackgroundJobResponse: {
            /** Job Id */
            job_id: string;
            /** Status Url */
            status_url: string;
        };
        /** BackgroundJobStatusResponse */
        BackgroundJobStatusResponse: {
            /** Job Id */
            job_id: string;
            /** Action */
            action: string;
            /**
             * Status
             * @enum {string}
             */
            status: "queued" | "running" | "retrying" | "succeeded" | "failed" | "superseded";
            /** Result */
            result?: {
                [key: string]: unknown;
            } | null;
            /** Error */
            error?: string | null;
        };
        /** ConstantFieldParser */
        ConstantFieldParser: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            rule: "constant";
            /** Constant Value */
            constant_value: string;
        };
        /** EmailDetail */
        EmailDetail: {
            /** Id */
            id: number;
            /** Message Id */
            message_id: string;
            /**
             * Received At
             * Format: date-time
             */
            received_at: string;
            /** Sender */
            sender: string;
            /** Subject */
            subject: string | null;
            /** Template Id */
            template_id: number | null;
            /** Body */
            body: string;
            representation: components["schemas"]["EmailDetailRepresentationResponse"] | null;
        };
        /** EmailDetailRepresentationResponse */
        EmailDetailRepresentationResponse: {
            /** Template Text */
            template_text: string;
            /** Extracted Parameters */
            extracted_parameters: components["schemas"]["IndexedParameterResponse"][];
            resolved_fields: components["schemas"]["ResolvedTransactionFields"];
        };
        /** EmailPage */
        EmailPage: {
            /** Items */
            items: components["schemas"]["EmailSummary"][];
            /** Total */
            total: number;
            /** Page */
            page: number;
            /** Page Size */
            page_size: number;
            /** Total Pages */
            total_pages: number;
        };
        /** EmailRepresentationResponse */
        EmailRepresentationResponse: {
            /** Template Text */
            template_text: string;
            resolved_fields: components["schemas"]["ResolvedTransactionFields"];
        };
        /** EmailSummary */
        EmailSummary: {
            /** Id */
            id: number;
            /** Message Id */
            message_id: string;
            /**
             * Received At
             * Format: date-time
             */
            received_at: string;
            /** Sender */
            sender: string;
            /** Subject */
            subject: string | null;
            /** Template Id */
            template_id: number | null;
            representation: components["schemas"]["EmailRepresentationResponse"] | null;
        };
        /** EmailSyncRequest */
        EmailSyncRequest: {
            /**
             * From Date
             * Format: date
             */
            from_date: string;
        };
        /** ExtractedFieldParser */
        ExtractedFieldParser: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            rule: "extracted";
            /** Parameter Indices */
            parameter_indices: number[];
        };
        /**
         * FieldParserSet
         * @description The complete fixed parser set; null and omitted values are unconfigured.
         */
        FieldParserSet: {
            /** Amount */
            amount?:
                | (
                      | components["schemas"]["ExtractedFieldParser"]
                      | components["schemas"]["ConstantFieldParser"]
                      | components["schemas"]["MissingFieldParser"]
                  )
                | null;
            /** Currency Code */
            currency_code?:
                | (
                      | components["schemas"]["ExtractedFieldParser"]
                      | components["schemas"]["ConstantFieldParser"]
                      | components["schemas"]["MissingFieldParser"]
                  )
                | null;
            /** Payee */
            payee?:
                | (
                      | components["schemas"]["ExtractedFieldParser"]
                      | components["schemas"]["ConstantFieldParser"]
                      | components["schemas"]["MissingFieldParser"]
                  )
                | null;
            /** Description */
            description?:
                | (
                      | components["schemas"]["ExtractedFieldParser"]
                      | components["schemas"]["ConstantFieldParser"]
                      | components["schemas"]["MissingFieldParser"]
                  )
                | null;
            /** Transaction Date */
            transaction_date?:
                | (
                      | components["schemas"]["ExtractedFieldParser"]
                      | components["schemas"]["ConstantFieldParser"]
                      | components["schemas"]["MissingFieldParser"]
                  )
                | null;
            /** Account Hint */
            account_hint?:
                | (
                      | components["schemas"]["ExtractedFieldParser"]
                      | components["schemas"]["ConstantFieldParser"]
                      | components["schemas"]["MissingFieldParser"]
                  )
                | null;
            /** Is Credit */
            is_credit?:
                | (
                      | components["schemas"]["ExtractedFieldParser"]
                      | components["schemas"]["ConstantFieldParser"]
                      | components["schemas"]["MissingFieldParser"]
                  )
                | null;
        };
        /**
         * FieldParserStatus
         * @enum {string}
         */
        FieldParserStatus: "needs_generation" | "needs_review" | "approved";
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        /** IndexedParameterResponse */
        IndexedParameterResponse: {
            /** Index */
            index: number;
            /** Mask Name */
            mask_name: string;
            /** Value */
            value: string | null;
        };
        /** MissingFieldParser */
        MissingFieldParser: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            rule: "missing";
        };
        /** ResolvedTransactionFields */
        ResolvedTransactionFields: {
            /** Amount */
            amount?: string | null;
            /** Currency Code */
            currency_code?: string | null;
            /** Payee */
            payee?: string | null;
            /** Description */
            description?: string | null;
            /** Transaction Date */
            transaction_date?: string | null;
            /** Account Hint */
            account_hint?: string | null;
            /** Is Credit */
            is_credit?: string | null;
        };
        /** TemplateAccountUpdate */
        TemplateAccountUpdate: {
            /** Account Id */
            account_id: number | null;
        };
        /**
         * TemplateClassification
         * @enum {string}
         */
        TemplateClassification: "transaction_alert" | "unclassified" | "not_transaction_alert";
        /** TemplateDetailResponse */
        TemplateDetailResponse: {
            /** Id */
            id: number;
            /** Text */
            text: string;
            /** Is Transaction Alert */
            is_transaction_alert: boolean | null;
            /** Email Count */
            email_count: number;
            /** Account Id */
            account_id: number | null;
            field_parser_status: components["schemas"]["FieldParserStatus"] | null;
            example: components["schemas"]["TemplateEmailExample"] | null;
        };
        /** TemplateEmailExample */
        TemplateEmailExample: {
            /** Id */
            id: number;
            /** Message Id */
            message_id: string;
            /**
             * Received At
             * Format: date-time
             */
            received_at: string;
            /** Sender */
            sender: string;
            /** Subject */
            subject: string | null;
            /** Template Id */
            template_id: number | null;
            /** Body */
            body: string;
        };
        /** TemplateFieldParsersResponse */
        TemplateFieldParsersResponse: {
            /** Template Id */
            template_id: number;
            /** Text */
            text: string;
            /**
             * Transaction Extraction Status
             * @enum {string}
             */
            transaction_extraction_status: "pending" | "succeeded" | "failed";
            /** Transaction Extraction Error */
            transaction_extraction_error: string | null;
            field_parser_status: components["schemas"]["FieldParserStatus"] | null;
            /** Example Email Id */
            example_email_id: number | null;
            /** Parameters */
            parameters: components["schemas"]["IndexedParameterResponse"][];
            parsers: components["schemas"]["FieldParserSet"];
            preview: components["schemas"]["ResolvedTransactionFields"] | null;
        };
        /** TemplatePage */
        TemplatePage: {
            /** Items */
            items: components["schemas"]["TemplateResponse"][];
            /** Total */
            total: number;
            /** Page */
            page: number;
            /** Page Size */
            page_size: number;
            /** Total Pages */
            total_pages: number;
        };
        /** TemplateResponse */
        TemplateResponse: {
            /** Id */
            id: number;
            /** Text */
            text: string;
            /** Is Transaction Alert */
            is_transaction_alert: boolean | null;
            /** Email Count */
            email_count: number;
            /** Account Id */
            account_id: number | null;
            field_parser_status: components["schemas"]["FieldParserStatus"] | null;
        };
        /** TransactionPage */
        TransactionPage: {
            /** Items */
            items: components["schemas"]["TransactionResponse"][];
            /** Total */
            total: number;
            /** Page */
            page: number;
            /** Page Size */
            page_size: number;
            /** Total Pages */
            total_pages: number;
        };
        /** TransactionResponse */
        TransactionResponse: {
            /** Id */
            id: number;
            /** Email Id */
            email_id: number;
            /** Account Id */
            account_id: number | null;
            /** Amount */
            amount: string | null;
            /** Currency Code */
            currency_code: string | null;
            /** Payee */
            payee: string | null;
            /** Description */
            description: string | null;
            /** Transaction Date */
            transaction_date: string | null;
            /** Account Hint */
            account_hint: string | null;
            /** Is Credit */
            is_credit: boolean | null;
            representation: components["schemas"]["EmailRepresentationResponse"] | null;
        };
        /** ValidationError */
        ValidationError: {
            /** Location */
            loc: (string | number)[];
            /** Message */
            msg: string;
            /** Error Type */
            type: string;
            /** Input */
            input?: unknown;
            /** Context */
            ctx?: Record<string, never>;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    list_accounts_accounts_get: {
        parameters: {
            query?: {
                page?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AccountPage"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_account_accounts_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AccountCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AccountResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_account_accounts__account_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                account_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AccountResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    remove_account_accounts__account_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                account_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_account_accounts__account_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                account_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AccountUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AccountResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_emails_emails_get: {
        parameters: {
            query?: {
                page?: number;
                template_id?: number | "null" | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EmailPage"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_email_emails__email_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                email_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EmailDetail"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_templates_templates_get: {
        parameters: {
            query?: {
                page?: number;
                classification?: components["schemas"]["TemplateClassification"][] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TemplatePage"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_template_templates__template_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                template_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TemplateDetailResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_template_account_templates__template_id__account_put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                template_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TemplateAccountUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TemplateResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_field_parsers_templates__template_id__field_parsers_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                template_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TemplateFieldParsersResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    put_field_parsers_templates__template_id__field_parsers_put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                template_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FieldParserSet"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TemplateFieldParsersResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    post_approve_field_parsers_templates__template_id__field_parsers_approve_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                template_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TemplateFieldParsersResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    post_generate_field_parsers_templates__template_id__field_parsers_generate_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                template_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BackgroundJobResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    sync_email_email_sync_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["EmailSyncRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BackgroundJobResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    extract_transactions_action_transaction_extraction_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BackgroundJobResponse"];
                };
            };
        };
    };
    list_transactions_transactions_get: {
        parameters: {
            query?: {
                page?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TransactionPage"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_job_jobs__job_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                job_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BackgroundJobStatusResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
}
