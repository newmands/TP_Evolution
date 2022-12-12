def calc_capex(self, basic_economical_settings: BasicEconomicalSettings):
    """

    Args:
        basic_economical_settings:

    Returns:

    """

    """ get basic economical settings"""
    base_year = basic_economical_settings.start_year
    end_year = basic_economical_settings.end_year
    total_time_period = basic_economical_settings.total_time_period
    inflation = basic_economical_settings.estimated_inflation_rate
    interest_rate = basic_economical_settings.basic_interest_rate

    component_capex = None

    """ check if input parameters are given"""
    if self.economical_parameters is not None:
        component_capex = self.economical_parameters.component_capex

        database_capex_element = self.economical_parameters.get_capex_element_by_name('DATABASE')
        if self.economical_parameters.get_database_bool() is True:
            capex_elements = [database_capex_element]
        else:
            capex_elements = self.economical_parameters.get_all_capex_elements()
            if database_capex_element is not None:
                capex_elements.remove(database_capex_element)

            """loop through all elements of one component"""
        if capex_elements != None:
            for capex_element in capex_elements:

                """get element input parameters"""
                element_name = capex_element.get_name()
                investment_cost = capex_element.get_investment_costs()
                investment_function = capex_element.get_investment_function()
                funding = capex_element.get_funding_volume()
                lifecycle = capex_element.get_life_cycle()
                price_dev_factor = capex_element.get_price_dev_factor()
                risk_factor = capex_element.get_risk_surcharge_factor()
                if capex_element.interest_rate_factor is None:
                    interest_rate = basic_economical_settings.basic_interest_rate_factor
                    """-1 because interest_rate_factor is in basic settings, but interest rate has to be given to capex_element"""
                    capex_element.set_interest_rate(interest_rate - 1)
                else:
                    interest_rate = capex_element.interest_rate_factor

                """define timeframes"""
                reference_year = capex_element.get_reference_year() if capex_element.get_reference_year() is not None \
                    else basic_economical_settings.get_basic_reference_year()
                if capex_element.get_investment_year() is None:
                    investment_year = base_year
                    capex_element.set_investment_year(base_year)
                else:
                    investment_year = capex_element.get_investment_year()
                project_delay_time = base_year - reference_year
                element_time_period = end_year - investment_year + 1
                element_delay_time = investment_year - base_year
                total_delay_time = investment_year - reference_year

                price_dev_with_inflation = price_dev_factor + inflation

                """adjust the costs for the first investment for the year of investment"""
                if investment_cost is not None:
                    first_investment = investment_cost * price_dev_with_inflation ** (
                        total_delay_time) * risk_factor
                    funded_first_investment = (investment_cost - funding) * price_dev_with_inflation ** (
                        total_delay_time) * risk_factor
                elif investment_function is not None and self.size is not None:
                    first_investment = float(investment_function(self.size, total_delay_time)) * self.size
                    funded_first_investment = (first_investment - funding * price_dev_with_inflation ** (
                        total_delay_time)) * risk_factor
                else:
                    first_investment = 0
                    logging.warning(
                        f'Could not calculate CAPEX for {self.__class__.__name__, self.technology} of element {element_name}')

                """-------------calculate annuities as described in VDI 2067-----------------"""
                all_investments_element = []
                all_investments_not_discounted = []
                all_investments_not_discounted.append(funded_first_investment)
                all_investments_element.append(funded_first_investment)

                if lifecycle != 0:
                    """calculate annuity for elements which have a lifecycle e.g. electrolysis stacks"""

                    """calculate number costs for replacements"""
                    number_replacements = math.floor(element_time_period / lifecycle)

                    if number_replacements >= 1:
                        for replacement in range(1, number_replacements + 1):
                            if investment_cost is not None:
                                replacement_invest = float(
                                    first_investment * price_dev_with_inflation ** (replacement * lifecycle))
                            elif investment_function is not None and self.size is not None:
                                replacement_invest = float(investment_function(self.size,
                                                                               total_delay_time + (
                                                                                       replacement * lifecycle)) * self.size)
                            else:
                                replacement_invest = 0

                            replacement_invest_discounted = replacement_invest / (
                                    interest_rate ** (replacement * lifecycle))

                            all_investments_not_discounted.insert(replacement, replacement_invest)
                            all_investments_element.insert(replacement, replacement_invest_discounted)

                    """calculate remain value
                    -> discounting remain value to element invest_year"""

                    remain_value_element = all_investments_not_discounted[-1] * \
                                           ((number_replacements + 1) * lifecycle - element_time_period) / \
                                           lifecycle * \
                                           interest_rate ** (-element_time_period)

                    """ ------------------------ calculate annuity of capex ----------------------------------"""
                    annuity_factor = vdi.annuity_factor(interest_rate, total_time_period)
                    total_investment_element = sum(all_investments_element)

                    capex_annuity_element = (total_investment_element - remain_value_element) * \
                                            annuity_factor * interest_rate ** -element_delay_time

                else:
                    """calculation for elements which have no lifecycle e.g. research & development"""
                    capex_annuity_element = first_investment / total_time_period

                """write capex_Data in ExportDataclass"""
                element_capex = ElementCAPEX(element_name=element_name, all_investments=all_investments_element,
                                             input_parameters=capex_element,
                                             annuity=capex_annuity_element, remain_value=remain_value_element)
                self.economic_results.component_CAPEX.append(element_capex)
