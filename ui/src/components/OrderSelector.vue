<template>
  <v-select
    v-model="selectedValue"
    :items="options"
    :list-props="{ nav: true }"
    :menu-props="{ offsetY: true, bottom: true, nudgeTop: 8 }"
    density="compact"
    label="Order by"
    class="select--segmented"
    variant="outlined"
    attach
    single-line
    @update:model-value="emitValue"
  >
    <template #prepend>
      <v-tooltip location="bottom">
        <template #activator="{ props }">
          <v-btn
            v-bind="props"
            variant="text"
            height="32"
            @click="changeOrder"
            @keyup.enter="changeOrder"
          >
            <v-icon small>
              {{ icon }}
            </v-icon>
          </v-btn>
        </template>
        <span> {{ descending ? 'Descending ' : 'Ascending ' }} order </span>
      </v-tooltip>
    </template>
  </v-select>
</template>
<script>
export default {
  name: 'OrderSelector',
  emits: ['update:value'],
  props: {
    /** Objects should have title and value properties */
    options: {
      type: Array,
      required: true
    },
    default: {
      type: String,
      required: false,
      default: undefined
    }
  },
  data() {
    return {
      descending: true,
      selectedValue: this.default
    }
  },
  computed: {
    value() {
      return `${this.descending ? '-' : ''}${this.selectedValue}`
    },
    icon() {
      return this.descending ? 'mdi-sort-descending' : 'mdi-sort-ascending'
    }
  },
  methods: {
    emitValue() {
      this.$emit('update:value', this.value)
    },
    changeOrder() {
      this.descending = !this.descending
      if (this.selectedValue) {
        this.emitValue()
      }
    }
  }
}
</script>
<style lang="scss" scoped>
.select--segmented {
  max-width: fit-content;

  .v-select__selection {
    margin-top: 0;
    height: 37px;
  }

  :deep(.v-field) {
    font-size: 0.875rem;
    font-weight: 500;
  }

  :deep(.v-input__prepend) {
    border: solid rgba(0, 0, 0, 0.15);
    border-width: 1px 0 1px 1px;
    border-radius: 4px 0 0 4px;
    margin: 0;
  }

  :deep(.v-input__prepend) + .v-input__control > .v-field--center-affix {
    border-radius: 0 4px 4px 0;
  }

  :deep(.v-field__outline) {
    --v-field-border-opacity: 0.15;
  }
}
</style>
